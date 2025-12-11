"""
Коллекция промптов для виртуальной примерки одежды
"""

# Основной промпт (используется сейчас)
TRYON_PROMPT_V1 = """Virtual clothing try-on task:

FIRST IMAGE = the person trying on clothes (the customer).
OTHER IMAGES = the clothing items to try on.

IMPORTANT! KEEP FROM THE FIRST IMAGE:
- The person (their face, body type, height, pose, arms, legs, skin tone)
- The background (keep it exactly as is)
- The lighting and color scheme
- The photo quality and style

CHANGE ONLY THE CLOTHING:
- Put the clothing from other images onto THE PERSON FROM THE FIRST IMAGE
- The clothing should fit naturally on their body
- Include realistic fabric folds, draping, and fit
- The clothing should match the person's pose

DO NOT CHANGE:
- The person (DO NOT replace them with the model from the clothing photos!)
- The background (keep the background from the first image!)
- The pose and body position
- The person's physical features

Result: same person, same background, new clothing only."""


# Альтернативный промпт 1: Более короткий и директивный
TRYON_PROMPT_V2 = """Dress the person from the FIRST image in the clothing from the OTHER images.

Rules:
- KEEP: person's face, body, pose, background, lighting (from image 1)
- CHANGE: only the clothing (from other images)
- DO NOT replace the person with models from clothing photos
- Make clothing fit naturally with realistic folds

Output: same person + same background + new clothing."""


# Альтернативный промпт 2: С примером "как не надо"
TRYON_PROMPT_V3 = """Virtual try-on: Dress the person from image 1 in clothing from other images.

CORRECT result:
✅ Person from image 1 wearing clothing from other images
✅ Background from image 1
✅ Person's face, body, and pose preserved

INCORRECT result:
❌ Model from clothing photo in customer's background
❌ Changing person's appearance
❌ Changing background

Keep everything from image 1 except the clothing.
Replace only the clothing with items from other images.
Make clothing fit naturally on the person's body."""


# Альтернативный промпт 3: Step-by-step инструкция
TRYON_PROMPT_V4 = """Virtual clothing try-on. Follow these steps:

Step 1: Identify the person in the FIRST image (this is the customer)
Step 2: Identify the clothing items in OTHER images
Step 3: Keep the person, their pose, face, body, and background from image 1
Step 4: Replace ONLY their clothing with items from other images
Step 5: Make sure clothing fits naturally with proper folds and draping

Critical: The person from image 1 must remain in the final result.
Only their clothing should change. Background stays the same."""


# Альтернативный промпт 4: Технический (для профессиональных моделей)
TRYON_PROMPT_V5 = """Task: Virtual garment transfer

Input:
- Reference image (1): person in current clothing
- Source images (2+): target garments

Process:
1. Extract person's body pose and shape from reference image
2. Preserve: face, skin tone, body proportions, background, lighting
3. Transfer garments from source images onto reference person
4. Adjust for realistic fit: wrinkles, shadows, fabric behavior
5. Maintain spatial consistency and perspective

Output: Reference person wearing source garments in original setting.

Critical constraint: Do not swap the person with garment model."""


# Альтернативный промпт 5: Очень короткий (для быстрых моделей)
TRYON_PROMPT_V6 = """Put clothing from images 2+ onto the person from image 1.
Keep person, background, and lighting from image 1.
Only change the clothing."""


# Промпт для валидации результата (можно использовать отдельно)
VALIDATION_PROMPT = """Analyze this try-on result. Answer these questions:
1. Is the person's face the same as in the original photo? (yes/no)
2. Is the background the same as in the original photo? (yes/no)
3. Does the clothing fit naturally on the body? (yes/no)
4. Are there any obvious artifacts or errors? (yes/no)

Provide brief answers."""


# Промпт для улучшения качества результата
REFINEMENT_PROMPT = """Improve this virtual try-on result:
- Fix any unnatural clothing folds or wrinkles
- Adjust shadows and lighting to match the scene
- Ensure clothing edges blend naturally with the body
- Remove any artifacts or inconsistencies
Keep the person, pose, and background unchanged."""


# ===== НОВЫЕ ПРОМПТЫ ДЛЯ КОНТРОЛИРУЕМОЙ ПРИМЕРКИ =====

# Промпт для примерки ТОЛЬКО конкретного товара (не весь образ)
TRYON_SINGLE_ITEM = """Virtual try-on task: Try on ONLY the specific clothing item.

FIRST IMAGE = the person trying on clothes (the customer).
OTHER IMAGES = reference photos showing the specific item: {item_name}

IMPORTANT! KEEP FROM THE FIRST IMAGE:
- The person (their face, body type, height, pose, arms, legs, skin tone)
- The background (keep it exactly as is)
- The person's OTHER clothing items (shoes, accessories, other garments)
- The lighting and color scheme
- The photo quality and style

CHANGE ONLY THIS SPECIFIC ITEM:
- Replace ONLY the {item_name} on the person
- Keep all other clothing items that the person is wearing
- The {item_name} should fit naturally on their body
- Include realistic fabric folds, draping, and fit
- The clothing should match the person's pose

DO NOT CHANGE:
- The person (DO NOT replace them with the model from the clothing photos!)
- The background (keep the background from the first image!)
- Other clothing items the person is wearing
- The pose and body position
- The person's physical features

Result: same person, same background, same other clothes, but wearing the {item_name} from reference images."""


# Промпт для примерки ВСЕГО образа (вся одежда модели)
TRYON_FULL_OUTFIT = """Virtual try-on task: Try on the COMPLETE outfit from reference.

FIRST IMAGE = the person trying on clothes (the customer).
OTHER IMAGES = reference photos showing a complete outfit/look.

IMPORTANT! KEEP FROM THE FIRST IMAGE:
- The person (their face, body type, height, pose, arms, legs, skin tone)
- The background (keep it exactly as is)
- The lighting and color scheme
- The photo quality and style

CHANGE ALL CLOTHING:
- Put the COMPLETE outfit from other images onto THE PERSON FROM THE FIRST IMAGE
- Replace ALL clothing items (top, bottom, shoes, accessories visible on model)
- All clothing should fit naturally on their body
- Include realistic fabric folds, draping, and fit
- The clothing should match the person's pose

DO NOT CHANGE:
- The person (DO NOT replace them with the model from the clothing photos!)
- The background (keep the background from the first image!)
- The pose and body position
- The person's physical features

Result: same person, same background, but wearing the COMPLETE outfit from reference images."""
