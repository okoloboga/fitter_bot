"""
Коллекция промптов для виртуальной примерки одежды
"""

# Промпт для валидации результата (можно использовать отдельно)
VALIDATION_PROMPT = """Analyze this try-on result. Answer these questions:
1. Is the person's face the same as in the original photo? (yes/no)
2. Is the background the same as in the original photo? (yes/no)
3. Does the clothing fit naturally on the body? (yes/no)
4. Are there any obvious artifacts or errors? (yes/no)

Provide brief answers."""

# ===== НОВЫЕ ПРОМПТЫ ДЛЯ КОНТРОЛИРУЕМОЙ ПРИМЕРКИ =====

# Промпт для примерки ТОЛЬКО конкретного товара (не весь образ)
TRYON_SINGLE_ITEM = """Virtual clothing try-on task:

MAIN IMAGE = Image 1: the person trying on clothes (the customer).
REFERENCE OTHER IMAGES = Image 2: the {category} item to try on.

IMPORTANT! KEEP FROM THE MAIN IMAGE:
- The person (their face, body type, height, pose, arms, legs, skin tone)
- The background (keep it exactly as is)
- The lighting and color scheme
- The photo quality and style

CHANGE ONLY THE CLOTHING:
- Put the clothing item from the reference images onto THE PERSON FROM THE MAIN IMAGE
- The new clothing should replace only the matching item the person is wearing
- The clothing should fit naturally on their body
- Include realistic fabric folds, draping, and fit
- The clothing should match the person's pose

DO NOT CHANGE:
- The person (DO NOT replace them with the model from the clothing photos!)
- The background (keep the background from the main image!)
- The pose and body position
- The person's physical features

Result: same person, same background, new single clothing item only."""

# Промпт для примерки ВСЕГО образа (вся одежда модели)
TRYON_FULL_OUTFIT = """
Virtual clothing try-on task:

MAIN IMAGE = Image 1: the person trying on clothes (the customer).
REFERENCE OTHER IMAGES = Image 2: the full outfit to try on.

IMPORTANT! KEEP FROM THE MAIN IMAGE:
- The person (their face, body type, height, pose, arms, legs, skin tone)
- The background (keep it exactly as is)
- The lighting and color scheme
- The photo quality and style

CHANGE ONLY THE CLOTHING:
- Put the full outfit from the reference images onto THE PERSON FROM THE MAIN IMAGE
- Replace all clothing on the person with the outfit from Image 2
- The outfit should fit naturally on their body
- Include realistic fabric folds, draping, and fit
- The outfit should match the person's pose

DO NOT CHANGE:
- The person (DO NOT replace them with the model from the clothing photos!)
- The background (keep the background from the main image!)
- The pose and body position
- The person's physical features

Result: same person, same background, wearing the full outfit from the reference.
"""
