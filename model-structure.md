# UstazOn Database Structure

## Overview

UstazOn database consists of 30+ tables organized into 5 main areas:
- **Core**: Users and authentication
- **Educational Structure**: Subjects, institutions, and content organization
- **Content**: Learning materials (Cards, QMJ, Tests, Games)
- **User Features**: Subscriptions, favorites, AI chat
- **Teaching Materials**: AI-generated lesson plans and tests

---

## 1. Core (Users & Auth)

### User
Main user table for teachers.

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| iin | String(12) | Kazakhstan ID (unique) |
| name | String(100) | Full name |
| phone | String(15) | Phone number (unique) |
| hashed_password | String(255) | BCrypt hash |
| is_active, is_verified | Boolean | Account status |
| is_admin, is_superuser | Boolean | Permissions |

**Relationships:**
- One-to-many: subscriptions, chat_conversations, teaching_materials

### VerificationCode
SMS verification codes for registration and password reset.

| Field | Type | Description |
|-------|------|-------------|
| phone | String(15) | Phone number |
| code | String(6) | 6-digit code |
| purpose | String(20) | "register" or "reset_password" |
| is_used | Boolean | Code usage status |
| expires_at | DateTime | Expiration time |

---

## 2. Educational Structure

### InstitutionType
Type of educational institution.

| Field | Description | Example |
|-------|-------------|---------|
| name | Institution name | "Мектеп" (School) |
| code | Unique code | "school" |

**Relationships:**
- Many-to-many with: subjects, qmj, cards, games
- One-to-many: subscriptions

### Subject
Academic subjects.

| Field | Description | Example |
|-------|-------------|---------|
| name | Subject name | "Математика" |
| code | Unique code | "math" |
| image_url | Subject icon | |
| hero_image_url | Header image | |

**Relationships:**
- Many-to-many with: institution_types, windows, cards, qmj, games
- One-to-many: subscriptions

### Template
Categories for organizing materials.

| Field | Description | Example |
|-------|-------------|---------|
| name | Template name | "Презентация" |
| code_name | Unique code | "presentation" |

**Relationships:**
- One-to-many: windows

### Window
Sections/categories for grouping content.

| Field | Type | Description |
|-------|------|-------------|
| name | String(100) | Window name |
| template_id | ForeignKey | Parent template |
| link | String(255) | Optional URL |
| nsub | Boolean | Requires subscription |
| image_url | String(500) | Thumbnail |

**Relationships:**
- Many-to-one: template
- Many-to-many: subjects

---

## 3. Content

### Card (Educational Materials)
Main content cards - 2M+ materials for teachers.

| Field | Type | Description |
|-------|------|-------------|
| name | Text | Material title |
| description | Text | Description |
| grade | Integer | Grade 1-11 |
| quarter | Integer | Quarter 1-4 |
| topic_id | ForeignKey | Topic (tree structure) |
| window_id | ForeignKey | Category |
| file_path | String(500) | Uploaded file |
| url | String(500) | External URL |
| img1_url...img5_url | String(500) | Preview images (PDF screenshots) |
| video1_url | String(500) | Video content |
| author_id | ForeignKey | Creator |

**Relationships:**
- Many-to-many with: subjects, institution_types, users (favorites)
- Many-to-one: topic (CardTopic), window, author (User)

**Indexes:** grade+quarter, author+created_at

### CardTopic
Hierarchical topic structure (tree).

| Field | Description |
|-------|-------------|
| topic | Topic name |
| parent_topic_id | Self-referencing ForeignKey |

**Relationships:**
- Self-referencing: parent/children
- One-to-many: cards

### QMJ (Lesson Plans)
Short-term lesson plans (ҚМЖ - Kazakhstan education standard).

| Field | Type | Description |
|-------|------|-------------|
| title | Text | Lesson title |
| text | Text | Learning objectives |
| grade | Integer | Grade 1-11 |
| quarter | Integer | Quarter 1-4 |
| code | String(50) | Subject code |
| hour | Integer | Duration (hours) |
| order | Integer | Sequence number |
| file | String(500) | Main file |
| author_id | ForeignKey | Creator |

**Relationships:**
- Many-to-many with: subjects, institution_types
- One-to-many: files (QMJFile)

### QMJFile
File attachments for lesson plans (multiple files support).

| Field | Type | Description |
|-------|------|-------------|
| file | String(500) | File path |
| file_size | Integer | Size in bytes |
| file_type | String(10) | PDF, DOC, DOCX, TXT, RTF |
| qmj_id | ForeignKey | Parent lesson plan |
| uploaded_by_id | ForeignKey | Uploader |

### Test
Educational tests for students.

| Field | Type | Description |
|-------|------|-------------|
| title | String(200) | Test title |
| subject | String(200) | Subject name |
| duration | Integer | Minutes |
| difficulty | String(10) | easy/medium/hard |
| user_id | ForeignKey | Creator |

**Relationships:**
- One-to-many: questions, results, links

### Question
Questions in tests.

| Field | Type | Description |
|-------|------|-------------|
| test_id | ForeignKey | Parent test |
| text | Text | Question text |
| photo, video | String(500) | Media attachments |
| order | Integer | Question order |

**Relationships:**
- Many-to-one: test
- One-to-many: answers

### Answer
Answers to questions.

| Field | Type | Description |
|-------|------|-------------|
| question_id | ForeignKey | Parent question |
| text | String(500) | Answer text |
| is_correct | Boolean | Correct answer flag |
| order | Integer | Answer order |

### TestResult
Student test results with anti-cheat.

| Field | Type | Description |
|-------|------|-------------|
| test_id | ForeignKey | Test reference |
| student_name | String(200) | Student name |
| group_name | String(200) | Group/class |
| correct_answers | Integer | Score |
| total_questions | Integer | Total |
| percentage | Float | Score % |
| warning_count | Integer | Tab switches (anti-cheat) |
| attempt_count | Integer | Attempt number |
| started_at, completed_at | DateTime | Time tracking |

### TestLink
Shareable test links for groups.

| Field | Type | Description |
|-------|------|-------------|
| test_id | ForeignKey | Test reference |
| unique_hash | String(100) | URL hash (unique) |
| group_name | String(200) | Target group |
| is_active | Boolean | Link status |
| max_attempts | Integer | Attempt limit |
| expires_at | DateTime | Expiration |
| attempts_count | Integer | Usage counter |

### Game
17 types of educational games (quiz, match, memory, etc.).

| Field | Type | Description |
|-------|------|-------------|
| title | String(255) | Game title |
| description | Text | Description |
| template_id | ForeignKey | Game type (17 types) |
| difficulty | String(10) | easy/medium/hard |
| grade, quarter | Integer | Educational level |
| time_limit | Integer | Seconds |
| is_public | Boolean | Public/private |
| is_featured | Boolean | Featured game |
| password | String(255) | Optional protection |
| settings | JSON | Custom settings |
| views_count, plays_count, likes_count | Integer | Stats |
| author_id | ForeignKey | Creator |

**Relationships:**
- Many-to-one: template (GameTemplate), author, topic
- Many-to-many with: subjects, institution_types, categories, users (favorites)
- One-to-many: items, results, links, ratings

### GameTemplate
17 game types (quiz, flashcards, crossword, etc.).

| Field | Type | Description |
|-------|------|-------------|
| name | String(100) | Template name |
| game_type | String(20) | Enum: quiz/match/memory/etc. |
| description | Text | Description |
| min_items, max_items | Integer | Item constraints |
| default_settings | JSON | Default config |
| is_premium | Boolean | Premium feature |

**Game Types:** quiz, match, flashcards, memory, spin_wheel, fill_blanks, drag_drop, group_sort, word_cloud, ranking, puzzle, typing, wordsearch (premium), crossword (premium), anagram (premium), maze_chase (premium), timeline (premium)

### GameItem
Questions/items in games.

| Field | Type | Description |
|-------|------|-------------|
| game_id | ForeignKey | Parent game |
| item_type | String(20) | text/image/audio/video/pair/group |
| question, answer | Text | Content |
| answer_options | JSON | Multiple choice options |
| hint, explanation | Text | Help text |
| image, audio, video | String(500) | Media files |
| points | Integer | Score value |
| order | Integer | Item order |
| extra_data | JSON | Game-specific data |

### GameResult
Game play results.

| Field | Type | Description |
|-------|------|-------------|
| game_id | ForeignKey | Game reference |
| score, max_score | Integer | Points |
| percentage | Float | Score % |
| correct_answers, total_questions | Integer | Stats |
| time_spent | Integer | Seconds |
| player_name, group_name | String(255) | Player info |
| answers_data | JSON | Detailed answers |
| player_id | ForeignKey | User (optional) |

### GameLink
Shareable game links.

| Field | Type | Description |
|-------|------|-------------|
| game_id | ForeignKey | Game reference |
| unique_hash | String(64) | URL hash |
| group_name | String(255) | Target group |
| password | String(255) | Optional protection |
| expires_at | DateTime | Expiration |
| max_attempts | Integer | Usage limit |
| is_active | Boolean | Link status |

### GameRating
User ratings for games (1-5 stars).

| Field | Type | Description |
|-------|------|-------------|
| game_id, user_id | ForeignKey | Unique per user+game |
| rating | Integer | 1-5 stars |
| comment | Text | Review text |

### GameCategory
Game categories for organization.

| Field | Type | Description |
|-------|------|-------------|
| name | String(100) | Category name |
| description | Text | Description |
| icon, color | String | UI styling |
| order | Integer | Display order |

---

## 4. User Features

### Subscribe (Subscription)
User subscriptions to subjects.

| Field | Type | Description |
|-------|------|-------------|
| user_id | ForeignKey | User |
| subject_id | ForeignKey | Subject |
| institution_type_id | ForeignKey | Institution type |
| end_date | Date | Expiration date |

**Property:** `is_active` - checks if end_date >= today

### PageAccess
URL pattern-based access control.

| Field | Type | Description |
|-------|------|-------------|
| url_pattern | String(255) | URL pattern (unique) |
| name | String(100) | Readable name |
| protection_level | String(50) | public/auth_only/subscription_required/admin_only |
| requires_specific_subject | Boolean | Subject-specific access |
| subject_id, institution_type_id | ForeignKey | Optional filters |
| is_active | Boolean | Rule status |

### ChatConversation
AI chat sessions.

| Field | Type | Description |
|-------|------|-------------|
| user_id | ForeignKey | User |
| title | String(200) | Auto-generated title |
| subject | String(50) | Topic (math, physics, etc.) |
| message_count | Integer | Message counter |
| total_tokens | Integer | Token usage |

**Relationships:**
- One-to-many: messages

### ChatMessage
Individual chat messages.

| Field | Type | Description |
|-------|------|-------------|
| conversation_id | ForeignKey | Parent conversation |
| role | String(20) | "user" or "model" |
| content | Text | Message text |
| input_tokens, output_tokens, total_tokens | Integer | Token tracking |
| extra_data | JSON | Attachments, metadata |

---

## 5. Teaching Materials

### TeachingMaterial
AI-generated educational content.

| Field | Type | Description |
|-------|------|-------------|
| user_id | ForeignKey | Creator |
| material_type | Enum | lesson_plan/test/homework/rubric |
| title | String(300) | Title |
| subject | String(100) | Subject name |
| grade | String(50) | Grade level |
| topic | String(300) | Topic |
| content | JSON | Material content (varies by type) |
| ai_model | String(50) | AI model used |
| difficulty_level | Enum | easy/medium/hard/mixed |
| estimated_time | Integer | Minutes |
| question_count | Integer | For tests/homework |
| tags | JSON | Search tags |
| view_count, download_count | Integer | Usage stats |

---

## Key Patterns

### Many-to-Many Relationships
- `card_subject` - Cards ↔ Subjects
- `card_institution_type` - Cards ↔ InstitutionTypes
- `card_favorites` - Users ↔ Cards (favorites)
- `subject_institution_type` - Subjects ↔ InstitutionTypes
- `subject_window` - Subjects ↔ Windows
- `qmj_subjects`, `qmj_institution_types` - QMJ associations
- `game_subjects`, `game_institution_types`, `game_categories`, `game_favorites` - Game associations

### Hierarchical Structures
- `CardTopic` - Self-referencing tree (parent_topic_id)

### Anti-Cheat & Tracking
- `TestResult.warning_count` - Tab switches during test
- `TestResult.attempt_count` - Multiple attempts
- `GameResult.time_spent` - Time tracking
- `GameResult.ip_address`, `user_agent` - Metadata

### Access Control
- `Window.nsub` - Requires subscription flag
- `PageAccess` - URL pattern-based permissions
- `Game.password` - Optional password protection
- `TestLink`, `GameLink` - Shareable links with expiration and limits

### File Management
- Cards: `file_path`, `img1_url`...`img5_url`, `video1_url`
- QMJ: `file` + separate `QMJFile` table for multiple files
- Questions: `photo`, `video`
- GameItems: `image`, `audio`, `video`

### Soft References
- `author_id`, `uploaded_by_id` - SET NULL on user deletion (preserve content)
- Most content uses CASCADE delete for parent-child relationships

---

## Database Statistics

- **Users**: Authentication + profile
- **Content Tables**: ~2M+ cards, growing QMJ/tests/games library
- **Association Tables**: 10+ many-to-many junction tables
- **Total Tables**: 30+ models covering education platform needs

## Technology

- **ORM**: SQLAlchemy 2.0 (async)
- **Database**: PostgreSQL
- **Migrations**: Alembic
- **Patterns**: Repository pattern, soft deletes, hierarchical data
