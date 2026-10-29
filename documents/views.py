import base64
import json
import os
from io import BytesIO
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from PIL import Image, ImageOps
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from .models import Document

# PyMuPDF for secure PDF handling & decryption
try:
    import fitz  # PyMuPDF

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

# Safe rembg & u2netp session initialization for Passport only
try:
    from rembg import remove, new_session

    REMBG_AVAILABLE = True
    u2netp_session = new_session('u2netp')
except Exception as e:
    print("Rembg initialization note:", e)
    REMBG_AVAILABLE = False
    u2netp_session = None


def kiosk_home_view(request):
    return render(request, 'documents/index.html')


def document_gallery_view(request):
    return render(request, 'documents/index.html')


@csrf_exempt
def delete_document_view(request, pk=None):
    if request.method == 'POST' or request.method == 'DELETE':
        try:
            doc_id = pk
            if not doc_id and request.body:
                data = json.loads(request.body)
                doc_id = data.get('id')

            if doc_id:
                doc = Document.objects.get(pk=doc_id)
                doc.delete()
                return JsonResponse({'success': True, 'message': 'Document deleted successfully'})
            return JsonResponse({'error': 'Document ID missing'}, status=400)
        except Document.DoesNotExist:
            return JsonResponse({'error': 'Document nahi mila'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=405)


@csrf_exempt
def upload_document_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            doc_type = data.get('doc_type')  # 'id_cards', 'passport', 'pan_card', 'voter_id'
            image_data = data.get('image_data')  # base64 string
            title = data.get('title', 'Cropped Document')
            apply_bg = data.get('apply_bg', False)
            bg_color = data.get('bg_color', '#ffffff')
            pdf_password = data.get('pdf_password')

            if not image_data:
                return JsonResponse({'error': 'Image data missing'}, status=400)

            # Check if initial upload is a Password-Protected PDF
            if image_data.startswith('data:application/pdf') or image_data.startswith('%PDF') or (
                    ';base64,' in image_data and 'application/pdf' in image_data.split(';base64,')[0]):
                header, imgstr = image_data.split(';base64,', 1) if ';base64,' in image_data else ('', image_data)
                image_bytes = base64.b64decode(imgstr)

                if not PYMUPDF_AVAILABLE:
                    return JsonResponse({'error': 'PyMuPDF installed nahi hai.'}, status=500)

                pdf_doc = fitz.open(stream=image_bytes, filetype="pdf")
                if pdf_doc.needs_pass:
                    if not pdf_password:
                        return JsonResponse({'error': 'PDF password required'}, status=400)
                    if not pdf_doc.authenticate(pdf_password):
                        return JsonResponse({'error': 'Password galat hai!'}, status=400)

                page = pdf_doc[0]
                pix = page.get_pixmap(dpi=200)
                img_bytes_extracted = pix.tobytes("jpeg")

                encoded_img = base64.b64encode(img_bytes_extracted).decode('utf-8')
                base64_data = f"data:image/jpeg;base64,{encoded_img}"

                return JsonResponse({'base64_data': base64_data})

            # Normal Cropped Image Upload (Base64)
            if ',' in image_data:
                imgstr = image_data.split(';base64,')[-1]
            else:
                imgstr = image_data

            image_bytes = base64.b64decode(imgstr)
            img = Image.open(BytesIO(image_bytes)).convert("RGB")

            if img.width < 10 or img.height < 10:
                return JsonResponse({'error': 'Uploaded image invalid ya blank hai.'}, status=400)

            # 🛑 1. AADHAAR / ID CARDS: Exact 8.6cm x 5.4cm (1016x638 px)
            if doc_type == 'id_cards':
                img = img.resize((1016, 638), Image.Resampling.LANCZOS)

            # 💳 2. PAN CARD: Exact 8.6cm x 5.4cm (1016x638 px)
            elif doc_type == 'pan_card':
                img = img.resize((1016, 638), Image.Resampling.LANCZOS)

            # 🗳️ 3. VOTER ID CARD: Exact 8.5cm x 5.5cm (1004x650 px)
            elif doc_type == 'voter_id':
                img = img.resize((1004, 650), Image.Resampling.LANCZOS)

            # 🎨 4. PASSPORT ONLY: Zero Face Bleed & Clean Solid Background
            elif doc_type == 'passport':
                img = img.resize((413, 531), Image.Resampling.LANCZOS)

                if apply_bg:
                    hex_color = bg_color.lstrip('#')
                    rgb_tuple = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

                    bg_applied = False
                    if REMBG_AVAILABLE and u2netp_session:
                        try:
                            img_rgba = img.convert("RGBA")
                            no_bg_img = remove(
                                img_rgba,
                                session=u2netp_session,
                                alpha_matting=False
                            )

                            r, g, b, a = no_bg_img.split()
                            clean_alpha = a.point(lambda p: 255 if p > 40 else 0)
                            no_bg_img.putalpha(clean_alpha)

                            solid_bg = Image.new("RGBA", img.size, rgb_tuple + (255,))
                            solid_bg.paste(no_bg_img, (0, 0), no_bg_img)
                            img = solid_bg.convert("RGB")
                            bg_applied = True
                        except Exception as ex:
                            print("Rembg error:", ex)

                    if not bg_applied:
                        img = Image.new("RGB", (413, 531), rgb_tuple)

                border_width = 3
                img = ImageOps.expand(img, border=border_width, fill='black')

            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=95)
            file_content = ContentFile(buffer.getvalue())

            file_name = f"{doc_type}_{title.replace(' ', '_')}.jpg"

            doc = Document.objects.create(
                doc_type=doc_type,
                title=title
            )

            file_url = ''
            if hasattr(doc, 'image'):
                doc.image.save(file_name, file_content, save=True)
                file_url = doc.image.url if doc.image else ''
            elif hasattr(doc, 'raw_file'):
                doc.raw_file.save(file_name, file_content, save=True)
                file_url = doc.raw_file.url if doc.raw_file else ''

            return JsonResponse({
                'id': doc.id,
                'file_url': file_url
            })

        except Exception as e:
            print("Upload Error:", str(e))
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@csrf_exempt
def print_batch_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            doc_ids = data.get('document_ids', [])
            layout_type = data.get('layout_type', '4x6')  # '4x6' or 'A4'
            sheet_mode = data.get('sheet_mode',
                                  'id_cards')  # 'id_cards', 'passport', 'passport_12', 'pan_card', 'voter_id'

            docs_dict = {doc.id: doc for doc in Document.objects.filter(id__in=doc_ids)}
            docs = [docs_dict[did] for did in doc_ids if did in docs_dict]

            if not docs:
                return JsonResponse({'error': 'Print ke liye koi document nahi mila.'}, status=400)

            images = []
            for doc in docs:
                img_field = getattr(doc, 'image', None) or getattr(doc, 'raw_file', None) or getattr(doc,
                                                                                                     'processed_file',
                                                                                                     None)
                if img_field and hasattr(img_field, 'path') and os.path.exists(img_field.path):
                    loaded_img = Image.open(img_field.path).convert("RGB")
                    if loaded_img.width > 10 and loaded_img.height > 10:
                        images.append(loaded_img)

            if not images:
                return JsonResponse({'error': 'Images load nahi ho saki ya blank hain.'}, status=400)

            if layout_type == '4x6':
                sheet_w, sheet_h = 1800, 1200
            else:
                sheet_w, sheet_h = 2480, 3508

            sheet = Image.new("RGB", (sheet_w, sheet_h), (255, 255, 255))

            # 📸 PASSPORT GRID CHECK
            if 'passport' in sheet_mode:
                if '16' in sheet_mode:
                    cols, rows = 4, 4  # 4x4 = 16 Photos
                elif '12' in sheet_mode:
                    cols, rows = 3, 4  # 3x4 = 12 Photos
                elif '8' in sheet_mode:
                    cols, rows = 2, 4  # 2x4 = 8 Photos
                else:
                    cols = 3
                    rows = 3 if sheet_mode == 'passport' else 3  # Default 9 Photos
                margin_x = 100
                margin_y = 100
                spacing_x = 50
                spacing_y = 50

                avail_w = sheet_w - (2 * margin_x) - ((cols - 1) * spacing_x)
                avail_h = sheet_h - (2 * margin_y) - ((rows - 1) * spacing_y)

                item_w = avail_w // cols
                item_h = int(item_w * (531 / 413))

                if item_h * rows > avail_h:
                    item_h = avail_h // rows
                    item_w = int(item_h * (413 / 531))

                pass_img = images[0].resize((item_w, item_h), Image.Resampling.LANCZOS)

                total_grid_w = (cols * item_w) + ((cols - 1) * spacing_x)
                total_grid_h = (rows * item_h) + ((rows - 1) * spacing_y)

                start_x = (sheet_w - total_grid_w) // 2
                start_y = (sheet_h - total_grid_h) // 2

                curr_x = start_x
                curr_y = start_y

                for r in range(rows):
                    for c in range(cols):
                        sheet.paste(pass_img, (curr_x, curr_y))
                        curr_x += pass_img.width + spacing_x
                    curr_x = start_x
                    curr_y += pass_img.height + spacing_y

            else:
                # ID Cards, PAN Card, Voter ID (Top & Bottom multi-cut sheet arrangement)
                y_offset = 60
                for img in images[:2]:
                    img_w, img_h = img.size
                    aspect = img_h / img_w

                    if sheet_mode == 'voter_id':
                        target_w = 1004 if layout_type != '4x6' else 900
                        target_h = int(target_w * aspect)
                    elif sheet_mode == 'pan_card':
                        target_w = 1016 if layout_type != '4x6' else 900
                        target_h = int(target_w * aspect)
                    else:
                        if layout_type == '4x6':
                            target_h = 520
                            target_w = int(target_h / aspect)
                        else:
                            target_w = 1016
                            target_h = 638

                    resized_img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                    x_pos = (sheet_w - target_w) // 2

                    sheet.paste(resized_img, (x_pos, y_offset))
                    y_offset += target_h + 30

            out_buffer = BytesIO()
            sheet.save(out_buffer, format='JPEG', quality=95)
            file_content = ContentFile(out_buffer.getvalue())

            file_name = f"print_sheet_{layout_type}_{sheet_mode}.jpg"
            saved_path = default_storage.save(f"documents/sheets/{file_name}", file_content)
            sheet_url = default_storage.url(saved_path)

            return JsonResponse({'print_sheet_url': sheet_url})

        except Exception as e:
            print("Print Batch Error:", str(e))
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


# Bulletproof Aliases
DocumentUploadView = upload_document_view
generate_kiosk_print_batch = print_batch_view