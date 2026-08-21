import ast
import os
import subprocess
import logging
from pathlib import Path
import shutil
import uuid
import re

logger = logging.getLogger(__name__)

# The code that reaches this service is written by an LLM from a
# user-supplied topic, then executed as a real Python process (via manim).
# That is a prompt-injection-to-RCE path: a user can steer the model into
# emitting arbitrary Python. This denylist is defense-in-depth only, not a
# real sandbox - it blocks the obvious escape routes (filesystem, network,
# process spawning, dynamic code loading, reflection tricks). The actual fix
# is to run this subprocess in an isolated, network-disabled, non-root,
# resource-limited container/sandbox at the infrastructure level.
DISALLOWED_MODULES = {
    "os", "sys", "subprocess", "shutil", "socket", "ctypes", "importlib",
    "pty", "pickle", "multiprocessing", "threading", "pathlib", "io",
    "code", "inspect", "gc", "ftplib", "http", "urllib", "requests",
    "asyncio", "signal", "resource", "sysconfig", "platform", "webbrowser",
    "smtplib", "telnetlib", "sqlite3",
}
DISALLOWED_CALLS = {
    "eval", "exec", "compile", "__import__", "open", "input", "globals",
    "locals", "vars", "getattr", "setattr", "delattr", "exit", "quit",
    "breakpoint",
}


class UnsafeManimCodeError(ValueError):
    """Raised when AI-generated Manim code contains disallowed constructs."""


def validate_manim_code_safety(code: str) -> None:
    """
    Reject AI-generated code that imports dangerous modules, calls dangerous
    builtins, or reaches for dunder attributes commonly used to escape
    restricted-exec sandboxes (e.g. ().__class__.__bases__).
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise UnsafeManimCodeError(f"Generated code has a syntax error: {e}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in DISALLOWED_MODULES:
                    raise UnsafeManimCodeError(f"Disallowed import: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in DISALLOWED_MODULES:
                raise UnsafeManimCodeError(f"Disallowed import: {node.module}")
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in DISALLOWED_CALLS:
                raise UnsafeManimCodeError(f"Disallowed call: {func.id}")
            if isinstance(func, ast.Attribute) and func.attr in DISALLOWED_CALLS:
                raise UnsafeManimCodeError(f"Disallowed call: {func.attr}")
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__") and node.attr.endswith("__"):
            raise UnsafeManimCodeError(f"Disallowed dunder attribute access: {node.attr}")


def sanitize_manim_code(code: str) -> str:
    """
    Sanitize AI-generated Manim code to fix common errors.
    Works line-by-line for better reliability.
    """
    lines = code.split('\n')
    sanitized_lines = []
    
    for line in lines:
        original_line = line
        
        # Skip comment lines
        if line.strip().startswith('#'):
            sanitized_lines.append(line)
            continue
        
        # Remove entire lines with problematic FadeOut patterns
        if 'FadeOut' in line and 'self.mobjects' in line:
            # Replace with a comment
            indent = len(line) - len(line.lstrip())
            sanitized_lines.append(' ' * indent + '# Removed: FadeOut(self.mobjects)')
            continue
        
        # Remove .add_coordinates() and similar chained methods (including multiline)
        # Handle: ).add_coordinates(...)
        line = re.sub(r'\.add_coordinates\s*\([^)]*\)', '', line)
        line = re.sub(r'\.add_numbers\s*\([^)]*\)', '', line)
        line = re.sub(r'\.add_labels\s*\([^)]*\)', '', line)
        
        # Remove lines with Sector(outer_radius=...) - buggy in Manim
        if 'Sector(' in line and 'outer_radius' in line:
            line = line.replace('outer_radius', 'radius')
        
        # Replace RightAngle with Elbow (simpler and works)
        if 'RightAngle(' in line:
            indent = len(line) - len(line.lstrip())
            sanitized_lines.append(' ' * indent + '# Removed: RightAngle (use Elbow instead)')
            continue
        
        # Replace MathTex with Text
        line = re.sub(r'MathTex\s*\(([^)]*)\)', r'Text(\1)', line)
        
        # Replace Tex with Text (but not MathTex which we already handled)
        line = re.sub(r'(?<!Math)Tex\s*\(([^)]*)\)', r'Text(\1)', line)
        
        # Replace Title with Text
        line = re.sub(r'Title\s*\(([^)]*)\)', r'Text(\1, font_size=48)', line)
        
        # Replace DecimalNumber with Text
        line = re.sub(r'DecimalNumber\s*\([^)]*\)', 'Text("0")', line)
        
        # Replace BulletedList with VGroup of Text
        if 'BulletedList(' in line:
            indent = len(line) - len(line.lstrip())
            sanitized_lines.append(' ' * indent + '# Removed: BulletedList')
            continue
        
        sanitized_lines.append(line)
    
    code = '\n'.join(sanitized_lines)
    
    # Ensure there's always a wait at the end
    if 'self.wait' not in code[-300:]:
        lines = code.strip().split('\n')
        for i in range(len(lines) - 1, -1, -1):
            stripped = lines[i].strip()
            if stripped and not stripped.startswith('#'):
                indent = len(lines[i]) - len(lines[i].lstrip())
                if 'self.wait' not in lines[i]:
                    lines.insert(i + 1, ' ' * indent + 'self.wait(2)')
                break
        code = '\n'.join(lines)
    
    return code


class ManimService:
    def __init__(self):
        self.output_dir = Path("media/manim_videos")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_video(self, code: str) -> str:
        """
        Executes Manim code and returns the path to the generated video file.
        """
        job_id = str(uuid.uuid4())
        job_dir = self.output_dir / job_id
        job_dir.mkdir(exist_ok=True)
        
        script_path = job_dir / "scene.py"
        
        # Sanitize code to fix common AI errors
        code = sanitize_manim_code(code)

        # Reject obviously dangerous code before it ever touches disk/subprocess
        validate_manim_code_safety(code)

        # Write code to file
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(code)

        try:
            # Extract class name from code
            match = re.search(r'class\s+(\w+)\s*\(.*Scene.*\):', code)
            scene_name = match.group(1) if match else "GenScene"

            # Run Manim command
            # -qm: Quality Medium (720p 60fps)
            # --media_dir: Output directory
            import sys
            cmd = [
                sys.executable, "-m", "manim", 
                "-qm", 
                "--media_dir", str(job_dir),
                str(script_path), 
                scene_name
            ]
            
            logger.info(f"Running Manim: {' '.join(cmd)}")

            # Using subprocess to run the command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes max (increased from 5)
            )

            if result.returncode != 0:
                logger.error(f"Manim execution failed: {result.stderr}")
                # Try to capture the last few lines of error
                error_msg = result.stderr[-500:] if result.stderr else "Unknown Manim error"
                raise Exception(f"Manim error: {error_msg}")

            # Find the output video file
            # Manim structure: media_dir/videos/scene/quality/SceneName.mp4
            # Search recursively for .mp4 as the structure might vary slightly
            mp4_files = list(job_dir.glob("**/*.mp4"))
            
            if not mp4_files:
                logger.error(f"Manim finished but no MP4 found. Stdout: {result.stdout}")
                raise Exception("Video file was not generated despite success exit code")

            video_file = mp4_files[0]

            # Move video to final location / clean up structure
            final_path = self.output_dir / f"{job_id}.mp4"
            shutil.move(str(video_file), str(final_path))
            
            # Cleanup output dir
            shutil.rmtree(str(job_dir), ignore_errors=True)

            return str(final_path)

        except subprocess.TimeoutExpired:
            shutil.rmtree(str(job_dir), ignore_errors=True)
            raise Exception("Video generation timed out (limit: 5 minutes)")
            
        except Exception as e:
            # Cleanup on error
            shutil.rmtree(str(job_dir), ignore_errors=True)
            logger.error(f"Manim service error: {e}")
            raise e

manim_service = ManimService()
