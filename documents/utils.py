import os
from PIL import Image, ImageEnhance
from .id_card_utils import generate_id_card_print_sheet


def process_document_image(image_path, output_path):
    """ Standard Image Processor """
    try:
        pil_img = Image.open(image_path).convert('RGB')
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        pil_img.save(output_path, quality=95)
        return True
    except Exception as e:
        print(f"Error processing image: {e}")
        return False


def extract_metadata_from_image(image_path, doc_type):
    """ Extracts mock or real metadata for the uploaded document """
    return {
        "document_number": "STUDIO_VERIFIED",
        "full_name": "Verified Citizen",
        "status": "Processed Successfully"
    }


def generate_print_sheet(image_paths, output_sheet_path, layout_type="4x6", sheet_mode="passport"):
    """
    Unified Route Dispatcher:
    - ID Cards Mode: Routes strictly to dual-part ID engine (No grid repetition).
    - Passport Mode: UNTOUCHED original 3.5x4.5cm 8/12-up grid logic.
    """
    if not image_paths:
        return False

    # Force ID card mode to use dedicated engine so it never tiles like a passport
    if sheet_mode == "id_cards" or len(image_paths) == 2:
        return generate_id_card_print_sheet(image_paths, output_sheet_path, layout_type)

    # Passport Grid Logic (Strict & Untouched)
    if layout_type == "A4":
        sheet_width, sheet_height = 2480, 3508
        margin = 120
        gap = 50
    else:  # 4x6 Photo Paper
        sheet_width, sheet_height = 1200, 1800
        margin = 60
        gap = 25

    sheet = Image.new("RGB", (sheet_width, sheet_height), (255, 255, 255))

    cols = 3 if sheet_mode == "passport_12" else 2
    rows = 4

    available_width = sheet_width - (margin * 2) - (gap * (cols - 1))
    available_height = sheet_height - (margin * 2) - (gap * (rows - 1))

    cell_width = available_width // cols
    cell_height = available_height // rows

    positions = []
    for r in range(rows):
        for c in range(cols):
            x = margin + c * (cell_width + gap)
            y = margin + r * (cell_height + gap)
            positions.append((x, y))

    total_slots = len(positions)
    expanded_paths = []
    if len(image_paths) == 1:
        expanded_paths = [image_paths[0]] * total_slots
    else:
        while len(expanded_paths) < total_slots:
            for p in image_paths:
                expanded_paths.append(p)
                if len(expanded_paths) == total_slots:
                    break

    for index, img_path in enumerate(expanded_paths[:total_slots]):
        if os.path.exists(img_path):
            try:
                card_img = Image.open(img_path).convert('RGB')
                card_img.thumbnail((cell_width, cell_height), Image.Resampling.LANCZOS)

                paste_x = positions[index][0] + (cell_width - card_img.width) // 2
                paste_y = positions[index][1] + (cell_height - card_img.height) // 2

                sheet.paste(card_img, (paste_x, paste_y))
            except Exception as e:
                print(f"Error pasting passport photo: {e}")

    os.makedirs(os.path.dirname(output_sheet_path), exist_ok=True)
    sheet.save(output_sheet_path, quality=95)
    return True