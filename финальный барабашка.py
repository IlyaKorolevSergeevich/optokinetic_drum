import tkinter as tk
from tkinter import simpledialog, messagebox
import math
import time
import cv2
import os
import threading
from datetime import datetime

TOTAL_STRIPES = 1
STRIPE_WIDTH = 120
GAP_WIDTH = 150
TOTAL_CYCLE = (STRIPE_WIDTH + GAP_WIDTH) * TOTAL_STRIPES
SPEED = 100.0

is_running = False
has_started = False
global_phase = 0.0
camera_recording = False
video_writer = None
cap = None
camera_initialized = False

modes = []
current_mode_index = 0
mode_start_time = 0
mode_duration = 0
accrued_time = 0
last_time = time.time()

root = tk.Tk()
root.attributes('-fullscreen', True)
canvas = tk.Canvas(root, bg='black', highlightthickness=0)
canvas.pack(fill=tk.BOTH, expand=True)

def toggle_fullscreen(event=None):
    root.attributes('-fullscreen', not root.attributes('-fullscreen'))
canvas.bind('<Double-Button-1>', toggle_fullscreen)

def start_camera_recording():
    global camera_recording, video_writer
    if camera_recording:
        return
    if not camera_initialized:
        print("Камера не инициализирована")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_folder = "recordings"
    os.makedirs(save_folder, exist_ok=True)
    filename = os.path.join(save_folder, f"recording_{timestamp}.avi")
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    fps = 30.0
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    video_writer = cv2.VideoWriter(filename, fourcc, fps, (frame_width, frame_height))

    if not video_writer.isOpened():
        print("Ошибка: не удалось создать VideoWriter")
        return

    camera_recording = True
    print(f"📹 Запись видео начата: {filename}")

def stop_camera_recording():
    global camera_recording, video_writer
    if camera_recording:
        camera_recording = False
        if video_writer:
            video_writer.release()
            video_writer = None
        print("Запись видео остановлена")

def camera_loop():
    global cap, camera_recording, video_writer
    cv2.namedWindow("Camera", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Camera", 640, 480)
    while cap and cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        cv2.imshow("Camera", frame)
        if camera_recording and video_writer:
            video_writer.write(frame)

        title = "📹 RECORDING" if camera_recording else "🔍 PREVIEW"
        cv2.setWindowTitle("Camera", title)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == 27:
            root.after(0, on_closing)
            break
    cv2.destroyWindow("Camera")

def start_camera_preview():
    global cap, camera_initialized
    if camera_initialized:
        return
    for index in range(5):
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if cap.isOpened():
            print(f"Камера найдена с индексом {index}")
            camera_initialized = True
            break
        else:
            cap.release()
    else:
        print("Не удалось открыть камеру.")
        return

    threading.Thread(target=camera_loop, daemon=True).start()
    print("📷 Камера запущена (режим предпросмотра)")

def release_camera():
    global cap, camera_initialized, camera_recording
    camera_recording = False
    if cap:
        cap.release()
        cap = None
        camera_initialized = False
    cv2.destroyAllWindows()

def on_key_press(event):
    global is_running, mode_start_time, accrued_time, has_started
    if event.keysym == 'Escape':
        on_closing()
    elif event.keysym == 'space' and has_started:
        if is_running:
            accrued_time = time.time() - mode_start_time
            is_running = False
            stop_camera_recording()
        else:
            mode_start_time = time.time() - accrued_time
            is_running = True
            start_camera_recording()

root.bind('<Key>', on_key_press)

def setup_modes():
    mode_count_str = simpledialog.askstring("Количество режимов",
                                            "Введите количество режимов:",
                                            parent=root)
    if mode_count_str is None:
        return
    try:
        mode_count = int(mode_count_str)
        if mode_count <= 0:
            messagebox.showerror("Ошибка", "Число должно быть больше нуля.")
            root.after(100, setup_modes)
            return
    except ValueError:
        messagebox.showerror("Ошибка", "Некорректный ввод. Введите целое число.")
        root.after(100, setup_modes)
        return

    for i in range(1, mode_count + 1):
        params = simpledialog.askstring(f"Режим {i}",
                                         "Введите параметры через пробел:\n"
                                         "длительность(сек) ширина_полосы расстояние_между_полосами скорость\n"
                                         "Скорость: положительная = вправо, отрицательная = влево, 0 = нет движения\n"
                                         "Пример: 10 120 150 100.0",
                                         parent=root)
        if params is None:
            root.after(100, setup_modes)
            return
        parts = params.strip().split()
        if len(parts) != 4:
            messagebox.showerror("Ошибка", "Нужно 4 параметра. Повторите ввод.")
            i -= 1
            continue
        try:
            duration = float(parts[0])
            stripe_width = float(parts[1])
            gap_width = float(parts[2])
            speed = float(parts[3])
            if duration <= 0 or stripe_width <= 0 or gap_width <= 0:
                messagebox.showerror("Ошибка", "Длительность, ширина, промежуток должны быть >0.")
                i -= 1
                continue
            modes.append({
                'duration': duration,
                'stripe_width': stripe_width,
                'gap_width': gap_width,
                'speed': speed
            })
        except ValueError:
            messagebox.showerror("Ошибка", "Ошибка преобразования чисел. Повторите ввод.")
            i -= 1
            continue

    start_animation()
    start_camera_preview()

def start_animation():
    global has_started, current_mode_index, is_running, mode_start_time, accrued_time
    if not modes:
        messagebox.showerror("Ошибка", "Нет режимов для запуска.")
        return
    has_started = True
    current_mode_index = 0
    set_mode(0)
    is_running = False
    mode_start_time = time.time()
    accrued_time = 0

def set_mode(index):
    global STRIPE_WIDTH, GAP_WIDTH, TOTAL_CYCLE, SPEED, mode_duration
    m = modes[index]
    STRIPE_WIDTH = m['stripe_width']
    GAP_WIDTH = m['gap_width']
    TOTAL_CYCLE = (STRIPE_WIDTH + GAP_WIDTH) * TOTAL_STRIPES
    SPEED = m['speed']
    mode_duration = m['duration']

def next_mode():
    global current_mode_index, mode_start_time, accrued_time, is_running, has_started
    if current_mode_index + 1 < len(modes):
        current_mode_index += 1
        set_mode(current_mode_index)
        mode_start_time = time.time()
        accrued_time = 0
    else:
        is_running = False
        has_started = False
        stop_camera_recording()

def draw():
    global global_phase, last_time, mode_start_time, accrued_time

    canvas.delete('all')
    now = time.time()

    if has_started and is_running:
        dt = now - last_time
        global_phase += SPEED * dt

        elapsed = now - mode_start_time
        if elapsed >= mode_duration:
            next_mode()
            last_time = now

    last_time = now

    w = canvas.winfo_width()
    h = canvas.winfo_height()
    if w <= 1 or h <= 1:
        root.after(10, draw)
        return

    for i in range(TOTAL_STRIPES):
        base_x = i * (STRIPE_WIDTH + GAP_WIDTH) + global_phase
        k_start = math.ceil((-base_x - STRIPE_WIDTH) / TOTAL_CYCLE)
        x = base_x + k_start * TOTAL_CYCLE
        while x < w:
            if x + STRIPE_WIDTH > 0:
                canvas.create_rectangle(x, 0, x + STRIPE_WIDTH, h, fill='white', outline='')
            x += TOTAL_CYCLE

    root.after(16, draw)

def on_closing():
    release_camera()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

start_camera_preview()
root.after(100, setup_modes)
draw()
root.mainloop()