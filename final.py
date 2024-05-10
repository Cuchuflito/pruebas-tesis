import tkinter as tk
from tkinter import Frame, Canvas, Entry, Button, StringVar, Radiobutton, NW, simpledialog
from PIL import Image, ImageTk
import cv2
import numpy as np
from sklearn.cluster import KMeans

class ImageSegmentationApp:
    def __init__(self, master):
        self.master = master
        master.title("Aplicación de Segmentación y Pintura de Imagen")

        # Cargar y procesar la imagen original
        self.original_image = cv2.imread('imagen_prueba/image.jpg')
        if self.original_image is None:
            raise FileNotFoundError("Imagen no encontrada.")
        self.original_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)
        self.segmented_image = self.original_image.copy()
        self.current_image = self.original_image.copy()
        self.painted_image = self.segmented_image.copy()
        self.displayed_image = self.painted_image.copy()

        self.scale = 1.0  # Escala inicial de la imagen
        self.offset_x = 0  # Desplazamiento horizontal
        self.offset_y = 0  # Desplazamiento vertical
        self.canvas_width = self.original_image.shape[1]
        self.canvas_height = self.original_image.shape[0]

        self.color_options = Frame(master)
        self.color_options.pack(side="top")
        self.color_var = StringVar(value="red")
        colors = {"Azul (Mar)": "blue", "Rojo (Urbano)": "red", "Verde (Forestal)": "green", "Amarillo (Agricultura)": "yellow"}
        for text, value in colors.items():
            Radiobutton(self.color_options, text=text, variable=self.color_var, value=value).pack(side="left")

        self.k_entry = Entry(self.color_options, width=5)
        self.k_entry.pack(side="left")
        self.k_entry.insert(0, "4")
        self.kmeans_button = Button(self.color_options, text="Segmentar", command=self.apply_kmeans)
        self.kmeans_button.pack(side="left")

        # Botones de zoom
        self.zoom_in_button = Button(self.color_options, text="Zoom In", command=self.zoom_in)
        self.zoom_in_button.pack(side="left")
        self.zoom_out_button = Button(self.color_options, text="Zoom Out", command=self.zoom_out)
        self.zoom_out_button.pack(side="left")

        # Radio buttons para modos de dibujo
        self.mode_var = StringVar(value="paint")
        self.drag_radio = Radiobutton(self.color_options, text="Arrastrar", variable=self.mode_var, value="drag")
        self.drag_radio.pack(side="left")
        self.paint_radio = Radiobutton(self.color_options, text="Pintar", variable=self.mode_var, value="paint")
        self.paint_radio.pack(side="left")
        self.lazo_radio = Radiobutton(self.color_options, text="Lazo", variable=self.mode_var, value="lazo")
        self.lazo_radio.pack(side="left")
        self.finish_polygon_button = Button(self.color_options, text="Finalizar Polígono", command=self.finish_polygon)
        self.finish_polygon_button.pack(side="left")

        # Frame para contener el canvas
        self.image_frame = Frame(master)
        self.image_frame.pack(side="bottom")

        # Canvas para mostrar la imagen
        self.canvas = Canvas(self.image_frame, cursor="cross")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.handle_click)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", self.reset_drag)

        # Variables para gestionar el polígono
        self.polygon_points = []
        self.is_drawing_polygon = False
        self.current_polygon = None

        self.show_segmented_image()

    def apply_kmeans(self):
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
        self.photo_image = ImageTk.PhotoImage(image=img)
        self.canvas.config(width=self.canvas_width, height=self.canvas_height)
        self.canvas.create_image(self.offset_x, self.offset_y, image=self.photo_image, anchor=NW)

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
        mask = np.zeros((self.painted_image.shape[0] + 2, self.painted_image.shape[1] + 2), np.uint8)
        cv2.floodFill(self.painted_image, mask, (x, y), color, (tolerance,) * 3, (tolerance,) * 3, flags=cv2.FLOODFILL_FIXED_RANGE)
        self.displayed_image = self.painted_image.copy()
        self.show_segmented_image()

    def start_drag(self, event):
        if event.x < self.canvas.winfo_rootx() + self.canvas.winfo_width() and event.y < self.canvas.winfo_rooty() + self.canvas.winfo_height():
            self.drag_start_x = event.x
            self.drag_start_y = event.y

    def drag(self, event):
        if hasattr(self, 'drag_start_x') and self.drag_start_x is not None:
            self.offset_x = max(min(self.offset_x + event.x - self.drag_start_x, 0), self.canvas_width - self.displayed_image.shape[1] * self.scale)
            self.offset_y = max(min(self.offset_y + event.y - self.drag_start_y, 0), self.canvas_height - self.displayed_image.shape[0] * self.scale)
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
        if self.is_drawing_polygon:
            label = simpledialog.askstring("Rotular Polígono", "Ingrese el rótulo del área:")
            if label:
                center_x = sum(x for x, y in self.polygon_points) / len(self.polygon_points)
                center_y = sum(y for x, y in self.polygon_points) / len(self.polygon_points)
                self.canvas.create_text(center_x, center_y, text=label, fill="blue")
            self.is_drawing_polygon = False

root = tk.Tk()
app = ImageSegmentationApp(root)
root.mainloop()
