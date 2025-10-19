from pyueye import ueye
import numpy as np
import cv2
import os, math

# --- Global vars for mouse position ---
mouse_x, mouse_y = -1, -1
click_points = []  # store points


def mouse_callback(event, x, y, flags, param):
    """
    Update mouse position and store click points for line drawing.
    """
    global mouse_x, mouse_y, click_points

    if event == cv2.EVENT_MOUSEMOVE:
        mouse_x, mouse_y = x, y

    if event == cv2.EVENT_LBUTTONDOWN:
        click_points.append((x, y))
        if len(click_points) > 2:
            click_points = click_points[-2:]  # keep last two points

  
        
def live_stream_with_capture(cam_id=2, ini_path="param_save.ini", output_dir="captures"):
    """
    Display live stream from IDS uEye camera, press 'P' to save an image.
    Shows live (x, y) pixel position and color under cursor.
    """
    global click_points  # <-- FIX: ensure we use the global variable

    os.makedirs(output_dir, exist_ok=True)
    print(click_points)
    # Create camera handle
    h_cam = ueye.HIDS(cam_id)
    ret = ueye.is_InitCamera(h_cam, None)
    if ret != ueye.IS_SUCCESS:
        raise RuntimeError(f"is_InitCamera failed: {ret}")

    # # Load .ini parameters
    # ini_file = ueye.c_char_p(ini_path.encode("utf-8"))
    if ini_path is True:
        ret = ueye.is_ParameterSet(h_cam, ueye.IS_PARAMETERSET_CMD_LOAD_FILE, None, 0)
        if ret != ueye.IS_SUCCESS:
            print(f"⚠️ Warning: Failed to load INI file ({ini_path}), continuing with defaults.")

    try:
        # Get AOI (image size)
        rect_aoi = ueye.IS_RECT()
        ret = ueye.is_AOI(h_cam, ueye.IS_AOI_IMAGE_GET_AOI, rect_aoi, ueye.sizeof(rect_aoi))
        width = int(rect_aoi.s32Width)
        height = int(rect_aoi.s32Height)

        # Set color mode for OpenCV
        ueye.is_SetColorMode(h_cam, ueye.IS_CM_BGR8_PACKED)

        # Allocate image memory
        mem_ptr = ueye.c_mem_p()
        mem_id = ueye.c_int()
        bits_per_pixel = 24
        ret = ueye.is_AllocImageMem(h_cam, width, height, bits_per_pixel, mem_ptr, mem_id)
        if ret != ueye.IS_SUCCESS:
            raise RuntimeError(f"is_AllocImageMem failed: {ret}")

        ueye.is_SetImageMem(h_cam, mem_ptr, mem_id)

        # Start live video
        ret = ueye.is_CaptureVideo(h_cam, ueye.IS_DONT_WAIT)
        if ret != ueye.IS_SUCCESS:
            raise RuntimeError(f"is_CaptureVideo failed: {ret}")

        print("🎥 Live stream started. Press 'P' to capture, 'Q' or 'ESC' to quit.")

        # Create display window and set mouse callback
        window_name = "uEye Live Stream"
        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, mouse_callback)

        img_counter = 0

        while True:
            # Capture current frame
            ueye.is_FreezeVideo(h_cam, ueye.IS_WAIT)

            # Get pitch and convert to numpy
            pitch = ueye.INT()
            ueye.is_InquireImageMem(h_cam, mem_ptr, mem_id, ueye.INT(), ueye.INT(), ueye.INT(), pitch)
            img_data = ueye.get_data(mem_ptr, width, height, bits_per_pixel, int(pitch.value), copy=True)
            frame = np.reshape(img_data, (height, width, 3))

            # # Draw cursor info if inside frame
            # if 0 <= mouse_x < width and 0 <= mouse_y < height:
            #     color_bgr = frame[mouse_y, mouse_x].tolist()
            #     text = f"({mouse_x}, {mouse_y}) BGR={color_bgr}"
            #     cv2.circle(frame, (mouse_x, mouse_y), 5, (0, 255, 255), 1)
            #     cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
            #                 0.7, (0, 255, 255), 2, cv2.LINE_AA)

            # Draw line if 2 points clicked
            if len(click_points) == 2:
                pt1, pt2 = click_points
                cv2.line(frame, pt1, pt2, (0, 0, 255), 2)
                length = math.hypot(pt2[0] - pt1[0], pt2[1] - pt1[1])
                mid_x = (pt1[0] + pt2[0]) // 2
                mid_y = (pt1[1] + pt2[1]) // 2
                cv2.putText(frame, f"{length:.1f}px ;  {length*5.3:.1f} micron", (mid_x + 10, mid_y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                # print(f"📏 Line length: {length:.1f} pixels (Press 'C' to clear)")

            cv2.imshow(window_name, frame)

            key = cv2.waitKey(1) & 0xFF

            # Press 'C' to clear the drawn line
            if key in [ord('c'), ord('C')]:
                click_points = []  # still works — global now
                print("🧹 Cleared line.")

            # Press 'P' to save image
            if key in [ord('p'), ord('P')]:
                img_counter += 1
                filename = os.path.join(output_dir, f"capture_{img_counter:03d}.png")
                cv2.imwrite(filename, frame)
                print(f"📸 Image saved: {filename}")
                add_text_to_image(filename, output_path=filename+"_annotated.png")
                print(f"📸 Image with annotation saved: {filename+"_annotated.png"}")

            # Press 'Q' or 'ESC' to quit
            if key in [ord('q'), 27]:
                print("🛑 Exiting live stream...")
                break

    finally:
        ueye.is_StopLiveVideo(h_cam, ueye.IS_FORCE_VIDEO_STOP)
        ueye.is_FreeImageMem(h_cam, mem_ptr, mem_id)
        ueye.is_ExitCamera(h_cam)
        cv2.destroyAllWindows()


def add_text_to_image(image_path, output_path="output.png"):
    """
    Ouvre une petite fenêtre pour entrer un texte à ajouter à l'image.
    Si aucun texte n'est saisi, l'image est sauvegardée sans texte.
    """
    # Charge l'image
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Impossible de lire l'image : {image_path}")

    # Fenêtre d'entrée de texte
    text = ""
    window_name = "Enter text (Press ENTER to validate, ESC to cancel)"
    cv2.namedWindow(window_name)

    # Fonction pour afficher l’image + texte actuel
    def show_preview():
        preview = img.copy()
        if text:
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 1.0
            color = (0, 0, 255)
            thickness = 2
            (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, thickness)
            margin = 10
            x = img.shape[1] - text_width - margin
            y = text_height + margin
            cv2.putText(preview, text, (x, y), font, font_scale, color, thickness, cv2.LINE_AA)
        cv2.imshow(window_name, preview)

    show_preview()

    # Lecture des touches pour écrire du texte
    while True:
        key = cv2.waitKey(0)

        if key == 27:  # ESC -> Annuler
            print("❌ Aucun texte ajouté.")
            cv2.destroyWindow(window_name)
            cv2.imwrite(output_path, img)
            return

        elif key in [13, 10]:  # ENTER
            break

        elif key == 8:  # BACKSPACE
            text = text[:-1]

        elif 32 <= key <= 126:  # caractères imprimables
            text += chr(key)

        show_preview()

    cv2.destroyWindow(window_name)

    # Si texte vide → rien à ajouter
    if not text.strip():
        print("❌ Aucun texte ajouté.")
        cv2.imwrite(output_path, img)
        return

    # Ajout du texte final
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.0
    color = (0, 0, 255)
    thickness = 2
    (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, thickness)
    margin = 10
    x = img.shape[1] - text_width - margin
    y = text_height + margin
    # cv2.putText(img, text, (x, y), font, font_scale, color, thickness, cv2.LINE_AA)

    cv2.imwrite(output_path, img)
    print(f"✅ Image sauvegardée avec texte : {output_path}")


if __name__ == "__main__":
    live_stream_with_capture(cam_id=2, ini_path=True, output_dir="data")
