import tkinter as tk
import pyperclip
import webbrowser
import keyboard
import pyautogui
import time
import threading
import sys
import signal
from PIL import Image, ImageGrab, ImageDraw
import io
import win32clipboard
import win32gui
import win32con
import pystray
from pystray import MenuItem as item

try:
    import uiautomation as auto
    import pythoncom
except ImportError:
    auto = None
    pythoncom = None

pyautogui.FAILSAFE = False

# ================= CONFIGURATION =================
CONFIG = {
    "HOTKEY": "ctrl+alt+g",
    "EXIT_HOTKEY": "ctrl+alt+q",
    "GEMINI_URL": "https://gemini.google.com/app",
    "PASTE_DELAY_NEW": 6.0,   
    "PASTE_DELAY_REUSE": 1.5, 
}
# =================================================

class GeminiDesktopTool:
    def __init__(self):
        self.should_exit = False
        self.should_show_popup = False
        self.reuse_session = True  # Remember last reuse checkbox state
        self.colors = {
            'bg': '#1e1e2e', 'fg': '#cdd6f4', 'accent': '#89b4fa',
            'secondary': '#313244', 'input_bg': '#45475a', 
            'text_dim': '#6c7086', 'success': '#a6e3a1'
        }

    def set_clipboard_image(self, image):
        try:
            output = io.BytesIO()
            image.convert("RGB").save(output, "BMP")
            data = output.getvalue()[14:]
            output.close()
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
            win32clipboard.CloseClipboard()
        except Exception as e:
            print(f"Clipboard Error: {e}")

    def get_clipboard_image(self):
        try:
            img = ImageGrab.grabclipboard()
            if isinstance(img, Image.Image):
                return img
        except: pass
        return None

    def _image_to_bytes(self, image):
        """Convert PIL Image to PNG bytes for Tkinter PhotoImage."""
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        return buffer.getvalue()

    def focus_gemini_window(self):
        """Find and focus Gemini browser window."""
        found_hwnd = None
        found_title = ""
        
        def callback(hwnd, _):
            nonlocal found_hwnd, found_title
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if "Gemini" in title or "gemini.google.com" in title:
                    found_hwnd = hwnd
                    found_title = title
                    return False
            return True
        
        try:
            win32gui.EnumWindows(callback, None)
        except:
            pass
        
        if found_hwnd:
            print(f"  Found window: {found_title[:50]}")
            try:
                if win32gui.IsIconic(found_hwnd):
                    win32gui.ShowWindow(found_hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(found_hwnd)
                time.sleep(0.5)
                return found_hwnd
            except Exception as e:
                print(f"  Focus failed: {e}")
                return found_hwnd
        else:
            print("  No Gemini window found")
        return None

    def capture_text(self):
        print("  Capturing text...")
        time.sleep(0.6)
        pyperclip.copy('')
        
        # Temporarily ignore SIGINT (Ctrl+C signal) during the copy simulation
        original_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
        try:
            # Use keyboard library instead of pyautogui for safer Ctrl+C
            keyboard.send('ctrl+c')
            time.sleep(0.4)
        finally:
            # Restore original handler
            signal.signal(signal.SIGINT, original_handler)
        
        result = pyperclip.paste()
        print(f"  Captured: {len(result)} chars")
        return result if result else ""

    def wait_for_gemini_ready(self, max_wait=15):
        """Wait for Gemini page to be ready by polling for window."""
        print(f"  Waiting for Gemini to load (max {max_wait}s)...")
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            hwnd = self.focus_gemini_window()
            if hwnd:
                time.sleep(0.8)
                try:
                    win32gui.SetForegroundWindow(hwnd)
                    print(f"  Gemini ready after {time.time() - start_time:.1f}s")
                    return True
                except:
                    pass
            time.sleep(0.3)
        
        print(f"  Timeout waiting for Gemini")
        return False

    def run_automation(self, text, images, reuse):
        """Paste text and images to Gemini, then send."""
        print(f"Running automation... (reuse={reuse}, images={len(images) if images else 0})")
        
        # Initialize UIA for this thread
        uia_init = None
        if auto:
            try:
                uia_init = auto.UIAutomationInitializerInThread()
            except:
                pass

        try:
            hwnd = self.focus_gemini_window() if reuse else None
            
            if not hwnd:
                print("  Opening new Gemini page...")
                webbrowser.open(CONFIG["GEMINI_URL"])
                hwnd = self.wait_for_gemini_ready(max_wait=15)
            
            if hwnd and win32gui.IsWindow(hwnd):
                print("  Focusing input area...")
                
                # Use coordinate-based clicking (UIA disabled due to complexity)
                try:
                    rect = win32gui.GetWindowRect(hwnd)
                    x, y, w, h = rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1]
                    
                    # Click in the input area - it's at the bottom center of the window
                    # The input box is typically about 150-200px from the bottom edge
                    click_x = x + w // 2
                    click_y = y + h - 160
                    
                    print(f"  Clicking at: ({click_x}, {click_y})")
                    pyautogui.click(click_x, click_y)
                    time.sleep(0.3)
                    # Click again to ensure focus
                    pyautogui.click(click_x, click_y)
                except Exception as e:
                    print(f"  Focus click failed: {e}")
            
            time.sleep(0.5)
            
            # Paste text
            print("  Pasting text...")
            pyperclip.copy(text)
            keyboard.send('ctrl+v')
            time.sleep(0.8)
            
            # Paste images if any
            if images:
                for i, img in enumerate(images):
                    print(f"  Pasting image {i+1}/{len(images)}...")
                    self.set_clipboard_image(img)
                    time.sleep(0.5)
                    keyboard.send('ctrl+v')
                    time.sleep(1.0)
            
            # Send
            keyboard.send('enter')
            print("Done!")
        finally:
            if uia_init:
                del uia_init

    def show_popup(self):
        print("Creating popup...")
        try:
            captured_text = self.capture_text()
            initial_img = self.get_clipboard_image()
            screenshot_container = [initial_img]
            
            root = tk.Tk()
            root.title("Gemini Assistant")
            root.geometry("600x680")
            root.configure(bg=self.colors['bg'])
            root.overrideredirect(True)
            root.attributes("-topmost", True)
            
            reuse_var = tk.BooleanVar(value=self.reuse_session)
            sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
            root.geometry(f"+{sw//2-300}+{sh//2-340}")

            title_bar = tk.Frame(root, bg=self.colors['secondary'], height=40)
            title_bar.pack(fill=tk.X)
            tk.Label(title_bar, text="GEMINI DESKTOP", bg=self.colors['secondary'], fg=self.colors['accent'], font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=15)
            tk.Button(title_bar, text="✕", command=root.destroy, bg=self.colors['secondary'], fg=self.colors['fg'], bd=0, padx=15).pack(side=tk.RIGHT)

            main = tk.Frame(root, bg=self.colors['bg'], padx=25, pady=15)
            main.pack(fill=tk.BOTH, expand=True)

            tk.Label(main, text="INSTRUCTION", bg=self.colors['bg'], fg=self.colors['accent'], font=("Segoe UI", 8, "bold")).pack(anchor='w')
            desc_entry = tk.Text(main, height=3, bg=self.colors['input_bg'], fg=self.colors['fg'], insertbackground='white', font=("Segoe UI", 10), relief='flat', padx=10, pady=8)
            desc_entry.pack(fill=tk.X, pady=(5, 12))
            desc_entry.insert("1.0", "")

            tk.Label(main, text="CONTENT", bg=self.colors['bg'], fg=self.colors['text_dim'], font=("Segoe UI", 8, "bold")).pack(anchor='w')
            content_entry = tk.Text(main, height=10, bg=self.colors['secondary'], fg=self.colors['fg'], insertbackground='white', font=("Segoe UI", 9), relief='flat', padx=10, pady=8)
            content_entry.pack(fill=tk.X, pady=(5, 10))
            content_entry.insert("1.0", captured_text)

            tk.Checkbutton(main, text="Reuse Gemini Window", variable=reuse_var, bg=self.colors['bg'], fg=self.colors['fg'], selectcolor=self.colors['secondary'], font=("Segoe UI", 9)).pack(anchor='w', pady=(0, 8))

            # Image container - now supports multiple images
            images_list = []
            if initial_img:
                images_list.append(initial_img)
            
            # Image preview frame
            img_frame = tk.Frame(main, bg=self.colors['bg'])
            img_frame.pack(fill=tk.X, pady=(0, 8))
            
            preview_frame = tk.Frame(img_frame, bg=self.colors['bg'])
            preview_frame.pack(fill=tk.X)
            
            def show_preview(img, root_ref):
                """Show enlarged preview of an image in a popup."""
                preview_win = tk.Toplevel(root_ref)
                preview_win.title("Image Preview")
                preview_win.configure(bg='#1e1e2e')
                preview_win.attributes("-topmost", True)
                
                # Resize image to fit screen (max 800x600)
                display_img = img.copy()
                display_img.thumbnail((800, 600))
                photo = tk.PhotoImage(data=self._image_to_bytes(display_img))
                
                lbl = tk.Label(preview_win, image=photo, bg='#1e1e2e')
                lbl.image = photo
                lbl.pack(padx=10, pady=10)
                
                # Show size info
                tk.Label(preview_win, text=f"Size: {img.width} x {img.height} | Click anywhere or press Esc to close", 
                        bg='#1e1e2e', fg='#6c7086', font=("Segoe UI", 8)).pack(pady=(0, 10))
                
                # Center the window
                preview_win.update_idletasks()
                w, h = preview_win.winfo_width(), preview_win.winfo_height()
                sw, sh = preview_win.winfo_screenwidth(), preview_win.winfo_screenheight()
                preview_win.geometry(f"+{sw//2-w//2}+{sh//2-h//2}")
                
                # Close on click or Escape
                preview_win.bind("<Button-1>", lambda e: preview_win.destroy())
                preview_win.bind("<Escape>", lambda e: preview_win.destroy())
            
            def update_image_preview():
                # Clear existing previews
                for widget in preview_frame.winfo_children():
                    widget.destroy()
                
                if not images_list:
                    tk.Label(preview_frame, text="No images (click 📷 to add)", bg=self.colors['bg'], fg=self.colors['text_dim'], font=("Segoe UI", 8)).pack(side=tk.LEFT)
                else:
                    tk.Label(preview_frame, text=f"{len(images_list)} image(s): ", bg=self.colors['bg'], fg=self.colors['success'], font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT)
                    for i, img in enumerate(images_list):
                        # Create thumbnail
                        thumb = img.copy()
                        thumb.thumbnail((40, 40))
                        photo = tk.PhotoImage(data=self._image_to_bytes(thumb))
                        
                        thumb_frame = tk.Frame(preview_frame, bg=self.colors['secondary'], padx=2, pady=2)
                        thumb_frame.pack(side=tk.LEFT, padx=2)
                        
                        lbl = tk.Label(thumb_frame, image=photo, bg=self.colors['secondary'], cursor="hand2")
                        lbl.image = photo  # Keep reference
                        lbl.pack()
                        
                        # Left-click to preview
                        def preview_img(event, image=img):
                            show_preview(image, root)
                        lbl.bind("<Button-1>", preview_img)
                        
                        # Right-click to remove
                        def remove_img(event, idx=i):
                            del images_list[idx]
                            update_image_preview()
                        lbl.bind("<Button-3>", remove_img)
            
            update_image_preview()
            
            # Focus instruction field after window is shown
            root.after(100, desc_entry.focus_set)

            def refresh_from_clipboard():
                img = self.get_clipboard_image()
                if img:
                    images_list.append(img)
                    update_image_preview()

            def do_screenshot():
                root.withdraw()
                time.sleep(0.3)
                
                # Take a screenshot of the entire screen to show as background
                screen_img = ImageGrab.grab()
                
                overlay = tk.Toplevel(root)
                overlay.attributes("-fullscreen", True, "-topmost", True)
                overlay.configure(bg='black')
                
                # Convert screen to PhotoImage
                screen_photo = tk.PhotoImage(data=self._image_to_bytes(screen_img))
                
                canvas = tk.Canvas(overlay, cursor="cross", highlightthickness=0)
                canvas.pack(fill="both", expand=True)
                
                # Draw the screen image on canvas
                canvas.create_image(0, 0, anchor='nw', image=screen_photo)
                canvas.screen_photo = screen_photo  # Keep reference
                
                # Variables for selection
                start_x, start_y = [0], [0]
                rect_id = [None]
                
                def on_press(e):
                    start_x[0], start_y[0] = e.x, e.y
                    if rect_id[0]:
                        canvas.delete(rect_id[0])
                    rect_id[0] = canvas.create_rectangle(e.x, e.y, e.x, e.y, outline='red', width=2)
                
                def on_drag(e):
                    if rect_id[0]:
                        canvas.coords(rect_id[0], start_x[0], start_y[0], e.x, e.y)
                
                def on_release(e):
                    x1, y1 = min(start_x[0], e.x), min(start_y[0], e.y)
                    x2, y2 = max(start_x[0], e.x), max(start_y[0], e.y)
                    overlay.destroy()
                    
                    if x2 - x1 > 10 and y2 - y1 > 10:
                        # Capture the selected region from the original screenshot
                        cropped = screen_img.crop((x1, y1, x2, y2))
                        images_list.append(cropped)
                        update_image_preview()
                    
                    root.deiconify()
                
                def on_escape(e):
                    overlay.destroy()
                    root.deiconify()
                
                canvas.bind("<ButtonPress-1>", on_press)
                canvas.bind("<B1-Motion>", on_drag)
                canvas.bind("<ButtonRelease-1>", on_release)
                overlay.bind("<Escape>", on_escape)

            btn_frame = tk.Frame(main, bg=self.colors['bg'])
            btn_frame.pack(fill=tk.X)
            tk.Button(btn_frame, text="📷 ADD SCREENSHOT", command=do_screenshot, bg=self.colors['secondary'], fg=self.colors['fg'], relief='flat', padx=12, pady=8).pack(side=tk.LEFT)
            tk.Button(btn_frame, text="📋 PASTE IMG", command=refresh_from_clipboard, bg=self.colors['secondary'], fg=self.colors['fg'], relief='flat', padx=12, pady=8).pack(side=tk.LEFT, padx=10)
            
            def on_send():
                instruction = desc_entry.get('1.0', tk.END).strip()
                content = content_entry.get('1.0', tk.END).strip()
                # Combine instruction and content, avoiding extra newlines
                if instruction and content:
                    full_text = f"{instruction}\n\n{content}"
                else:
                    full_text = instruction or content
                reuse = reuse_var.get()
                self.reuse_session = reuse  # Remember for next time
                imgs = images_list.copy()  # Copy the list
                root.destroy()
                threading.Thread(target=self.run_automation, args=(full_text, imgs, reuse), daemon=True).start()

            tk.Button(btn_frame, text="SEND TO GEMINI", command=on_send, bg=self.colors['accent'], fg=self.colors['bg'], font=("Segoe UI", 9, "bold"), relief='flat', padx=25, pady=8).pack(side=tk.RIGHT)
            
            print("  Popup ready.")
            root.mainloop()
            print("  Popup closed.")
        except Exception as e:
            print(f"Popup Error: {e}")
            import traceback
            traceback.print_exc()

    def on_hotkey(self):
        print(">>> Hotkey triggered! <<<")
        self.should_show_popup = True

    def on_exit(self, icon=None, item=None):
        """Exit the program (can be called from hotkey or tray menu)."""
        print("Exiting...")
        self.should_exit = True
        if icon:
            icon.stop()

    def create_tray_icon(self):
        """Create a simple icon for the system tray."""
        # Create a simple colored icon
        size = 64
        img = Image.new('RGB', (size, size), color=(137, 180, 250))  # Gemini-like blue
        draw = ImageDraw.Draw(img)
        # Draw a "G" shape
        draw.ellipse([8, 8, 56, 56], outline='white', width=6)
        draw.rectangle([32, 28, 56, 36], fill=(137, 180, 250))
        draw.line([32, 32, 48, 32], fill='white', width=6)
        return img

    def run(self):
        print(f"Gemini Tool Active.")
        print(f"  Trigger: {CONFIG['HOTKEY']}")
        print(f"  Exit: {CONFIG['EXIT_HOTKEY']}")
        print(f"  (Running in system tray)")
        print("-" * 30)
        
        # Register hotkeys
        keyboard.add_hotkey(CONFIG['HOTKEY'], self.on_hotkey, suppress=True)
        keyboard.add_hotkey(CONFIG['EXIT_HOTKEY'], lambda: self.on_exit())
        
        # Create system tray icon
        icon_image = self.create_tray_icon()
        menu = pystray.Menu(
            item(f"Gemini Tool ({CONFIG['HOTKEY']})", None, enabled=False),
            pystray.Menu.SEPARATOR,
            item('Exit', self.on_exit)
        )
        self.tray_icon = pystray.Icon("Gemini Tool", icon_image, "Gemini Desktop Tool", menu)
        
        # Run tray icon in a separate thread
        tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        tray_thread.start()
        
        # Main loop
        while not self.should_exit:
            if self.should_show_popup:
                self.should_show_popup = False
                time.sleep(0.2)
                self.show_popup()
            time.sleep(0.05)
        
        # Cleanup
        keyboard.unhook_all()
        try:
            self.tray_icon.stop()
        except:
            pass
        print("Exited.")

if __name__ == "__main__":
    tool = GeminiDesktopTool()
    tool.run()
