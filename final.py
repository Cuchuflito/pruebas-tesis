import tkinter as tk
from tkinter import Frame, Canvas, Entry, Button, StringVar, Radiobutton, simpledialog, NW
from PIL import Image, ImageTk, ImageDraw, ImageFont
import cv2
import numpy as np
from sklearn.cluster import KMeans
from shapely.geometry import Polygon

class ImageSegmentationApp:
    def __init__(self, master):
        self.master = master
        master.title("Aplicación de Segmentación y Pintura de Imagen")
        master.geometry("1280x720")
        master.resizable(False, False)

        self.canvas_width = 1040
        self.canvas_height = 720
        self.scale = 1.0

        self.init_variables()
        self.setup_ui()

    def init_variables(self):
        self.historia = []
        self.labels = []
        self.polygon_points = []
        self.is_drawing_polygon = False
        self.current_polygon = None
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.mode_var = StringVar(value="paint")
        self.color_var = StringVar(value="red")
        self.load_image('imagen_prueba/image.jpg')
        self.font = ImageFont.load_default()

    def load_image(self, image_path):
        self.original_image = cv2.imread(image_path)
        if self.original_image is None:
            raise FileNotFoundError("Imagen no encontrada.")
        self.original_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)
        self.segmented_image = self.original_image.copy()
        self.current_image = self.segmented_image.copy()
        self.painted_image = self.segmented_image.copy()
        self.displayed_image = self.painted_image.copy()

    def setup_ui(self):
        self.top_frame = Frame(self.master)
        self.top_frame.pack(side="top", fill="x")

        self.k_entry = Entry(self.top_frame, width=5)
        self.k_entry.pack(side="left")
        self.k_entry.insert(0, "4")
        self.kmeans_button = Button(self.top_frame, text="Segmentar", command=self.apply_kmeans)
        self.kmeans_button.pack(side="left")

        self.zoom_in_button = Button(self.top_frame, text="Zoom In", command=self.zoom_in)
        self.zoom_in_button.pack(side="left")
        self.zoom_out_button = Button(self.top_frame, text="Zoom Out", command=self.zoom_out)
        self.zoom_out_button.pack(side="left")

        self.color_options = Frame(self.master, width=200)
        self.color_options.pack(side="right", fill="y")
        self.color_var = StringVar(value="red")
        colors = {"Azul (Mar)": "blue", "Rojo (Urbano)": "red", "Verde (Forestal)": "green", "Amarillo (Agricultura)": "yellow"}
        for text, value in colors.items():
            Radiobutton(self.color_options, text=text, variable=self.color_var, value=value).pack()

        self.mode_frame = Frame(self.top_frame)
        self.mode_frame.pack(side="left")
        Radiobutton(self.mode_frame, text="Arrastrar", variable=self.mode_var, value="drag").pack(side="left")
        Radiobutton(self.mode_frame, text="Pintar", variable=self.mode_var, value="paint").pack(side="left")
        Radiobutton(self.mode_frame, text="Lazo", variable=self.mode_var, value="lazo").pack(side="left")
        self.finish_polygon_button = Button(self.top_frame, text="Finalizar Polígono", command=self.finish_polygon)
        self.finish_polygon_button.pack(side="left")

        self.image_frame = Frame(self.master)
        self.image_frame.pack(side="left", fill="both", expand=True)
        self.canvas = Canvas(self.image_frame, width=1040, height=720, cursor="cross")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self.handle_click)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", self.reset_drag)

        self.undo_button = Button(self.master, text="Deshacer", command=self.undo_last_action)
        self.undo_button.pack(side="bottom")
        self.show_segmented_image()
        
        
    def save_to_historia(self):
        current_state = {
            'displayed_image': self.displayed_image.copy(),
            'labels': self.labels[:],
            'polygon_points': self.polygon_points[:]
        }
        self.historia.append(current_state)

    def undo_last_action(self):
        if self.historia:
            state = self.historia.pop()
            self.displayed_image = state['displayed_image']
            self.labels = state['labels']
            self.polygon_points = state['polygon_points']
            if self.is_drawing_polygon:
                if self.current_polygon:
                    self.canvas.delete(self.current_polygon)
                self.current_polygon = None
                self.is_drawing_polygon = False
            self.show_segmented_image()
        else:
            print("No hay más acciones para deshacer.")

    def apply_kmeans(self):
        self.save_to_historia()
        k = int(self.k_entry.get())
        kmeans = KMeans(n_clusters=k, random_state=0)
        data = self.original_image.reshape((-1, 3)).astype(np.float32)
        kmeans.fit(data)
        self.segmented_image = kmeans.cluster_centers_[kmeans.labels_].reshape(self.original_image.shape).astype(np.uint8)
        self.current_image = self.segmented_image.copy()
        self.painted_image = self.segmented_image.copy()
        self.displayed_image = self.painted_image.copy()
        self.show_segmented_image()

    def show_segmented_image(self):
        resized_image = cv2.resize(self.displayed_image, None, fx=self.scale, fy=self.scale, interpolation=cv2.INTER_LINEAR)
        img = Image.fromarray(resized_image)
        draw = ImageDraw.Draw(img)
        draw.font = self.font

        for label, (center_x, center_y) in self.labels:
            screen_x = int(center_x * self.scale)
            screen_y = int(center_y * self.scale)

            box_width, box_height = draw.font.getbbox(label, anchor='lt')[2:]
            box_x = screen_x - box_width // 2
            box_y = screen_y - box_height // 2
            draw.rectangle([box_x - 2, box_y - 2, box_x + box_width + 2, box_y + box_height + 2], fill='black')
            draw.text((box_x, box_y), label, fill='white', font=self.font)

        self.photo_image = ImageTk.PhotoImage(image=img)
        self.canvas.config(width=self.canvas_width * self.scale, height=self.canvas_height * self.scale)
        self.canvas.create_image(self.offset_x, self.offset_y, image=self.photo_image, anchor=NW)
        
        
    def safe_polygon_centroid(self, points):
        #Encuentra un punto seguro dentro del polígono usando shapely.
        poly = Polygon(points)
        point = poly.representative_point()  # Devuelve un punto garantizado dentro del polígono
        return point.x, point.y


    def handle_click(self, event):
        mode = self.mode_var.get()
        if mode == "lazo":
            if not self.is_drawing_polygon:
                self.polygon_points = [(event.x, event.y)]
                self.is_drawing_polygon = True
                if self.current_polygon:
                    self.canvas.delete(self.current_polygon)
                self.current_polygon = self.canvas.create_polygon(self.polygon_points, outline='red', fill='', width=2)
            else:
                self.polygon_points.append((event.x, event.y))
                self.canvas.coords(self.current_polygon, sum(self.polygon_points, ()))
        elif mode == "paint":
            color_map = {"red": (255, 0, 0), "blue": (0, 0, 255), "green": (0, 255, 0), "yellow": (255, 255, 0)}
            chosen_color = color_map[self.color_var.get()]
            original_x = int((event.x - self.offset_x) / self.scale)
            original_y = int((event.y - self.offset_y) / self.scale)
            if 0 <= original_x < self.painted_image.shape[1] and 0 <= original_y < self.painted_image.shape[0]:
                self.paint_segment(original_x, original_y, chosen_color)
        elif mode == "drag":
            self.start_drag(event)

    def paint_segment(self, x, y, color):
        tolerance = 20
        self.save_to_historia()
        mask = np.zeros((self.painted_image.shape[0] + 2, self.painted_image.shape[1] + 2), np.uint8)
        cv2.floodFill(self.painted_image, mask, (x, y), color, (tolerance,) * 3, (tolerance,) * 3, flags=cv2.FLOODFILL_FIXED_RANGE)
        self.displayed_image = self.painted_image.copy()
        self.show_segmented_image()

    def start_drag(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def drag(self, event):
        if hasattr(self, 'drag_start_x') and self.drag_start_x is not None:
            self.offset_x += event.x - self.drag_start_x
            self.offset_y += event.y - self.drag_start_y
            self.drag_start_x = event.x
            self.drag_start_y = event.y
            self.show_segmented_image()

    def reset_drag(self, event):
        self.drag_start_x = None
        self.drag_start_y = None

    def zoom_in(self):
        if self.scale < 5:
            self.scale *= 1.1
            self.show_segmented_image()

    def zoom_out(self):
        if self.scale > 0.5:
            self.scale *= 0.9
            self.show_segmented_image()

    def finish_polygon(self):
        if self.is_drawing_polygon and self.polygon_points:
            label = simpledialog.askstring("Etiqueta", "Introduce el nombre del sector:")
            if label:
                self.save_to_historia()
                centroid_x, centroid_y = self.safe_polygon_centroid(self.polygon_points)
                scaled_centroid_x = int((centroid_x - self.offset_x) / self.scale)
                scaled_centroid_y = int((centroid_y - self.offset_y) / self.scale)
                self.labels.append((label, (scaled_centroid_x, scaled_centroid_y)))
                self.show_segmented_image()
                self.is_drawing_polygon = False
                self.polygon_points = []
            if self.current_polygon:
                self.canvas.delete(self.current_polygon)
                self.current_polygon = None

root = tk.Tk()
app = ImageSegmentationApp(root)
root.mainloop()