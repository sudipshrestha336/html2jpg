import os
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
from playwright.sync_api import sync_playwright

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Chromium's hard limit on canvas/image dimensions (per side, in pixels).
# Going above this causes screenshots to fail or render blank.
MAX_CHROMIUM_DIMENSION = 32767


def html_to_jpeg(html_path_or_url, output_path, quality=100, scale=2, viewport_width=1280, viewport_height=800,
                  status_callback=None):
    """Convert an HTML file (or URL) into a high-resolution JPEG screenshot using Playwright.

    scale: device scale factor. Higher = sharper, but capped automatically if the
    resulting pixel dimensions would exceed Chromium's internal canvas size limit.
    viewport_width/height: base CSS viewport size before scaling is applied
    """
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": viewport_width, "height": viewport_height},
            device_scale_factor=scale,
        )
        page.goto(html_path_or_url, wait_until="networkidle")

        # Many report/landing-page templates use scroll-triggered "reveal" animations
        # (IntersectionObserver) where sections stay invisible until scrolled into view.
        # A full-page screenshot doesn't naturally scroll through the page, so those
        # sections would otherwise be captured blank. Force everything visible first.
        page.add_style_tag(content="""
            .reveal,
            .capital-card,
            .output-card,
            .outcome-card,
            .activity-col {
                opacity: 1 !important;
                transform: none !important;
                transition: none !important;
                animation: none !important;
            }
        """)

        # Also flip the 'visible' class JS would normally add via IntersectionObserver,
        # in case other logic depends on it.
        page.evaluate("""
            document.querySelectorAll('.reveal').forEach(el => el.classList.add('visible'));
        """)

        # --- Fix for blank space when content is short ---
        # Many report/page templates force the page wrapper to fill the viewport
        # (e.g. height:100vh or min-height:100vh, meant for print/A4 layout).
        # This leaves large blank areas below short content when captured as an image.
        # Strip those forced heights so elements shrink to fit their actual content.
        page.add_style_tag(content="""
            html, body {
                height: auto !important;
                min-height: 0 !important;
            }
            .page, .container, .a4, .report-page, .sheet, .wrapper, .content, main {
                min-height: 0 !important;
                height: auto !important;
            }
        """)

        # Wait for webfonts/icons to finish loading before measuring layout,
        # since text reflow can change card/section heights.
        try:
            page.evaluate("document.fonts.ready.then(() => true)")
        except Exception:
            pass
        page.wait_for_timeout(300)

        # Measure the actual rendered content height after removing forced heights
        content_height = page.evaluate("document.documentElement.scrollHeight")

        # --- Auto-clamp scale to stay within Chromium's canvas dimension limit ---
        # The final rasterized image is (viewport_width * scale) x (content_height * scale).
        # If either side would exceed MAX_CHROMIUM_DIMENSION, reduce the scale so it fits.
        max_scale_by_width = MAX_CHROMIUM_DIMENSION / viewport_width
        max_scale_by_height = MAX_CHROMIUM_DIMENSION / max(content_height, 1)
        safe_scale = min(scale, max_scale_by_width, max_scale_by_height)

        if safe_scale < scale:
            if status_callback:
                status_callback(
                    f"Requested {scale}x exceeds max renderable size for this page — "
                    f"using {safe_scale:.2f}x instead."
                )
            # Re-create the page with the clamped scale factor, since device_scale_factor
            # must be set at page-creation time and can't be changed afterward.
            page.close()
            page = browser.new_page(
                viewport={"width": viewport_width, "height": viewport_height},
                device_scale_factor=safe_scale,
            )
            page.goto(html_path_or_url, wait_until="networkidle")
            page.add_style_tag(content="""
                .reveal, .capital-card, .output-card, .outcome-card, .activity-col {
                    opacity: 1 !important;
                    transform: none !important;
                    transition: none !important;
                    animation: none !important;
                }
            """)
            page.evaluate("""
                document.querySelectorAll('.reveal').forEach(el => el.classList.add('visible'));
            """)
            page.add_style_tag(content="""
                html, body { height: auto !important; min-height: 0 !important; }
                .page, .container, .a4, .report-page, .sheet, .wrapper, .content, main {
                    min-height: 0 !important; height: auto !important;
                }
            """)
            try:
                page.evaluate("document.fonts.ready.then(() => true)")
            except Exception:
                pass
            page.wait_for_timeout(300)
            content_height = page.evaluate("document.documentElement.scrollHeight")

        # Resize the viewport to exactly match the real content height so the
        # screenshot captures only the content, with no extra blank space.
        page.set_viewport_size({"width": viewport_width, "height": content_height})

        page.screenshot(path=output_path, type="jpeg", quality=quality, full_page=False)
        browser.close()


class HtmlToJpegApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("HTML to JPEG Converter")
        self.geometry("560x400")
        self.resizable(False, False)

        # --- Input file row ---
        self.input_label = ctk.CTkLabel(self, text="Input HTML file:")
        self.input_label.pack(pady=(20, 5), padx=20, anchor="w")

        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(fill="x", padx=20)

        self.input_entry = ctk.CTkEntry(input_frame, placeholder_text="Select an HTML file...")
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.browse_input_btn = ctk.CTkButton(
            input_frame, text="Browse", width=90, command=self.browse_input
        )
        self.browse_input_btn.pack(side="right")

        # --- Output file row ---
        self.output_label = ctk.CTkLabel(self, text="Output JPEG file:")
        self.output_label.pack(pady=(20, 5), padx=20, anchor="w")

        output_frame = ctk.CTkFrame(self, fg_color="transparent")
        output_frame.pack(fill="x", padx=20)

        self.output_entry = ctk.CTkEntry(output_frame, placeholder_text="Choose where to save the JPEG...")
        self.output_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.browse_output_btn = ctk.CTkButton(
            output_frame, text="Browse", width=90, command=self.browse_output
        )
        self.browse_output_btn.pack(side="right")

        # --- Resolution / quality options ---
        options_frame = ctk.CTkFrame(self, fg_color="transparent")
        options_frame.pack(fill="x", padx=20, pady=(20, 0))

        self.scale_label = ctk.CTkLabel(options_frame, text="Resolution scale:")
        self.scale_label.pack(side="left")

        self.scale_menu = ctk.CTkOptionMenu(
            options_frame,
            values=[
                "1x (standard)",
                "2x (sharp)",
                "3x (extra sharp)",
                "4x (ultra)",
                "5x (max)",
                "6x (max, may be slow)",
                "Custom...",
            ],
            command=self.on_scale_change,
        )
        self.scale_menu.set("2x (sharp)")
        self.scale_menu.pack(side="left", padx=10)

        # --- Custom scale entry (hidden unless "Custom..." selected) ---
        self.custom_scale_entry = ctk.CTkEntry(options_frame, placeholder_text="e.g. 4.5", width=80)

        # --- Convert button ---
        self.convert_btn = ctk.CTkButton(
            self, text="Convert to JPEG", command=self.start_conversion, height=40
        )
        self.convert_btn.pack(pady=25)

        # --- Status label ---
        self.status_label = ctk.CTkLabel(self, text="", text_color="gray", wraplength=500, justify="left")
        self.status_label.pack(pady=5)

    def on_scale_change(self, choice):
        if choice == "Custom...":
            self.custom_scale_entry.pack(side="left", padx=(0, 10))
        else:
            self.custom_scale_entry.pack_forget()

    def browse_input(self):
        file_path = filedialog.askopenfilename(
            title="Select HTML file",
            filetypes=[("HTML files", "*.html *.htm"), ("All files", "*.*")],
        )
        if file_path:
            self.input_entry.delete(0, "end")
            self.input_entry.insert(0, file_path)

    def browse_output(self):
        file_path = filedialog.asksaveasfilename(
            title="Save JPEG as",
            defaultextension=".jpg",
            filetypes=[("JPEG files", "*.jpg *.jpeg")],
        )
        if file_path:
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, file_path)

    def get_selected_scale(self):
        choice = self.scale_menu.get()
        if choice == "Custom...":
            raw = self.custom_scale_entry.get().strip()
            try:
                value = float(raw)
                if value <= 0:
                    raise ValueError
                return value
            except ValueError:
                messagebox.showwarning(
                    "Invalid scale", "Please enter a valid positive number for the custom scale (e.g. 4.5)."
                )
                return None
        # "1x (standard)", "6x (max, may be slow)" -> take the leading number
        return float(choice.split("x")[0])

    def start_conversion(self):
        input_path = self.input_entry.get().strip()
        output_path = self.output_entry.get().strip()

        if not input_path or not output_path:
            messagebox.showwarning("Missing info", "Please select both an input file and an output location.")
            return

        scale = self.get_selected_scale()
        if scale is None:
            return

        # Convert a plain local path into a file:// URL for Playwright
        if not input_path.startswith(("http://", "https://", "file://")):
            input_url = "file:///" + os.path.abspath(input_path).replace("\\", "/")
        else:
            input_url = input_path

        self.convert_btn.configure(state="disabled", text="Converting...")
        self.status_label.configure(text="Working, please wait...", text_color="gray")

        # Run conversion in a background thread so the UI doesn't freeze
        thread = threading.Thread(target=self.run_conversion, args=(input_url, output_path, scale))
        thread.start()

    def run_conversion(self, input_url, output_path, scale):
        try:
            def status_update(msg):
                self.after(0, lambda: self.status_label.configure(text=msg, text_color="orange"))

            html_to_jpeg(input_url, output_path, quality=100, scale=scale, status_callback=status_update)
            self.after(0, self.on_success, output_path)
        except Exception as e:
            self.after(0, self.on_error, str(e))

    def on_success(self, output_path):
        self.convert_btn.configure(state="normal", text="Convert to JPEG")
        self.status_label.configure(text=f"Saved: {output_path}", text_color="lightgreen")
        messagebox.showinfo("Done", f"JPEG saved successfully:\n{output_path}")

    def on_error(self, error_message):
        self.convert_btn.configure(state="normal", text="Convert to JPEG")
        self.status_label.configure(text="Conversion failed.", text_color="red")
        messagebox.showerror("Error", f"Something went wrong:\n{error_message}")


if __name__ == "__main__":
    app = HtmlToJpegApp()
    app.mainloop()