import os
import subprocess
import logging
from pathlib import Path
import shutil
import uuid
import re

logger = logging.getLogger(__name__)


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
        
        # specific fix for "AttributeError: Axes object has no attribute 'to_center'"
        # Use regex to be more robust against spacing (e.g. .to_center( ))
        line = re.sub(r'\.to_center\s*\([^)]*\)', '.move_to(ORIGIN)', line)
        
        # fix: "TypeError: Mobject.move_to() got an unexpected keyword argument 'alignment'"
        if 'move_to' in line and 'alignment=' in line:
             line = line.replace('alignment=', 'aligned_edge=')

        # fix: "AttributeError: 'numpy.ndarray' object has no attribute 'rotate'"
        # Pattern: normalize(...).rotate(...) -> rotate_vector(normalize(...), ...)
        # We capture the vector part (normalize(...)) and the angle part inside rotate(...)
        # This regex handles simple cases. Nested parentheses might need more complex parsing but this covers the reported case.
        match = re.search(r'(normalize\s*\([^)]+\))\s*\.rotate\s*\(([^)]+)\)', line)
        if match:
            vector_part = match.group(1)
            angle_part = match.group(2)
            line = line.replace(match.group(0), f"rotate_vector({vector_part}, {angle_part})")

        # fix: "AttributeError: NumberPlane object has no attribute 'x_unit_size'"
        # In modern Manim, NumberPlane doesn't have x_unit_size attribute
        # Replace with 1 (default unit size) or use get_x_unit_size() method
        line = re.sub(r'(\w+)\.x_unit_size', r'1', line)
        line = re.sub(r'(\w+)\.y_unit_size', r'1', line)

        
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
        self.temp_dir = Path("media/manim_temp")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.videos_dir = Path("uploads/videos")
        self.videos_dir.mkdir(parents=True, exist_ok=True)

    def generate_video(self, code: str) -> str:
        """
        Executes Manim code, saves the video to uploads/videos/,
        and returns the public relative URL.
        """
        job_id = str(uuid.uuid4())
        job_dir = self.temp_dir / job_id
        job_dir.mkdir(exist_ok=True)

        script_path = job_dir / "scene.py"

        # Sanitize code to fix common AI errors
        code = sanitize_manim_code(code)

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
                timeout=600  # 10 minutes max
            )

            if result.returncode != 0:
                logger.error(f"Manim execution failed: {result.stderr}")
                error_msg = result.stderr[-500:] if result.stderr else "Unknown Manim error"
                raise Exception(f"Manim error: {error_msg}")

            # Find the output video file
            mp4_files = list(job_dir.glob("**/*.mp4"))

            if not mp4_files:
                logger.error(f"Manim finished but no MP4 found. Stdout: {result.stdout}")
                raise Exception("Video file was not generated despite success exit code")

            video_file = mp4_files[0]

            # Move video to uploads/videos/ for static serving
            final_filename = f"{job_id}.mp4"
            final_path = self.videos_dir / final_filename
            shutil.move(str(video_file), str(final_path))

            # Cleanup temp dir
            shutil.rmtree(str(job_dir), ignore_errors=True)

            # Return public URL path
            return f"/uploads/videos/{final_filename}"

        except subprocess.TimeoutExpired:
            shutil.rmtree(str(job_dir), ignore_errors=True)
            raise Exception("Video generation timed out (limit: 10 minutes)")

        except Exception as e:
            # Cleanup on error
            shutil.rmtree(str(job_dir), ignore_errors=True)
            logger.error(f"Manim service error: {e}")
            raise e

manim_service = ManimService()
