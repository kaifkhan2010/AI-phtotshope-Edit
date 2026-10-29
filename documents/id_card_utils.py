import os
from PIL import Image, ImageEnhance

def generate_id_card_print_sheet(image_paths, output_sheet_path, layout_type="4x6"):
    """
    Strict ID Card Layout Engine:
    - Ensures ID cards NEVER tile like passport grids.
    - Exactly 2 slots on 4x6/A4 sheet: Top (Front) and Bottom (Back) only.
    """
    if not image_paths:
        return False

    if layout_type == "A4":
        sheet_width, sheet_height = 2480, 3508
        margin = 120
        gap = 60
    else:  # 4x6 Photo Paper @ 300 DPI
        sheet_width, sheet_height = 1200, 1800
        margin = 60
        gap = 40  # Cutting gap between front and back

    sheet = Image.new("RGB", (sheet_width, sheet_height), (255, 255, 255))

    target_w = sheet_width - (margin * 2)
    target_h = (sheet_height - (margin * 2) - gap) // 2

    top_y = margin
    bottom_y = margin + target_h + gap

    try:
        if len(image_paths) >= 2:
            # Dual crop mode: index 0 is Front, index 1 is Back
            front_img = Image.open(image_paths[0]).convert('RGB').resize((target_w, target_h), Image.Resampling.LANCZOS)
            back_img = Image.open(image_paths[1]).convert('RGB').resize((target_w, target_h), Image.Resampling.LANCZOS)
        elif len(image_paths) == 1:
            # Single raw image upload: auto-slice into top and bottom
            src_img = Image.open(image_paths[0]).convert('RGB')
            sw, sh = src_img.size
            half_h = sh // 2
            front_img = src_img.crop((0, 0, sw, half_h)).resize((target_w, target_h), Image.Resampling.LANCZOS)
            back_img = src_img.crop((0, half_h, sw, sh)).resize((target_w, target_h), Image.Resampling.LANCZOS)
        else:
            return False

        # Enhance quality for crisp text and QR codes
        for img in [front_img, back_img]:
            color_enhancer = ImageEnhance.Color(img)
            img = color_enhancer.enhance(1.2)
            sharp_enhancer = ImageEnhance.Sharpness(img)
            img = sharp_enhancer.enhance(1.3)

        sheet.paste(front_img, (margin, top_y))
        sheet.paste(back_img, (margin, bottom_y))

        os.makedirs(os.path.dirname(output_sheet_path), exist_ok=True)
        sheet.save(output_sheet_path, quality=95)
        return True
    except Exception as e:
        print(f"Error in ID card print generation: {e}")
        return False