import face_recognition
import cv2
import os
from datetime import datetime
import json
import sqlite3
import sys
import tkinter as tk
from tkinter import ttk

class AttendanceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Absen v1")

        self.label_subject = tk.Label(root, text="Pilih Mata Kuliah:")
        self.label_subject.pack(pady=10)

        self.combo_subject = ttk.Combobox(root, values=["Matematika", "Python", "Big Data", "AI", "Jarkom"])
        self.combo_subject.pack(pady=10)

        self.button_start_attendance = tk.Button(root, text="Mulai Absen", command=self.start_attendance_wrapper)
        self.button_start_attendance.pack(pady=10)

    def load_images_and_encodings(self):
        known_encodings = []
        known_info = []
        path = "data_mahasiswa"  # Ganti dengan path folder gambar

        for filename in os.listdir(path):
            if filename.endswith(".jpg") or filename.endswith(".png"):
                image = face_recognition.load_image_file(os.path.join(path, filename))

                try:
                    encoding = face_recognition.face_encodings(image)[0]
                    file_components = os.path.splitext(filename)[0].split('_')
                    nim = file_components[0]
                    name = '_'.join(file_components[1:-1])
                    class_name = file_components[-1]
                    known_info.append({"nim": nim, "name": name, "class": class_name})
                    known_encodings.append(encoding)
                except IndexError:
                    print(f"Peringatan: Tidak dapat menemukan wajah pada {filename}. File tersebut akan dilewati.")

        return known_encodings, known_info

    def mark_attendance(self, info, db_connection, marked_attendance):
        current_date = self.get_current_time().split()[0]

        cursor = db_connection.cursor()
        cursor.execute("SELECT * FROM attendance WHERE nim=? AND date=?", (info["nim"], current_date))
        existing_entry = cursor.fetchone()

        if existing_entry:
            if not marked_attendance.get(info["nim"], False):
                print(f"{info['name']} ({info['nim']}) sudah absen hari ini.")
                marked_attendance[info["nim"]] = True
        else:
            cursor.execute("INSERT INTO attendance (nim, name, class, date) VALUES (?, ?, ?, ?)",
                           (info["nim"], info["name"], info["class"], current_date))
            db_connection.commit()
            print(f"{info['name']} ({info['nim']}) berhasil absen.")
            marked_attendance[info["nim"]] = True

    def start_attendance(self, subject):
        self.root.destroy()  # Tutup jendela pemilihan mata kuliah

        video_capture = cv2.VideoCapture(0)  # Ganti dengan indeks kamera yang sesuai

        known_encodings, known_info = self.load_images_and_encodings()

        # Buat koneksi database SQLite
        db_connection = sqlite3.connect(f"absen_{subject.lower()}.db")  # Gunakan nama database sesuai mata kuliah yang dipilih
        cursor = db_connection.cursor()

        # Buat tabel kehadiran jika belum ada
        cursor.execute('''CREATE TABLE IF NOT EXISTS attendance
                          (id INTEGER PRIMARY KEY AUTOINCREMENT,
                           nim TEXT NOT NULL,
                           name TEXT NOT NULL,
                           class TEXT NOT NULL,
                           date TEXT NOT NULL)''')
        db_connection.commit()

        marked_attendance = {}
        try:
            while True:
                ret, frame = video_capture.read()

                face_locations = face_recognition.face_locations(frame)
                face_encodings = face_recognition.face_encodings(frame, face_locations)

                for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                    matches = face_recognition.compare_faces(known_encodings, face_encoding)

                    info = {"nim": "Unknown", "name": "Unknown", "class": "Unknown"}

                    if True in matches:
                        first_match_index = matches.index(True)
                        info = known_info[first_match_index]

                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                    font = cv2.FONT_HERSHEY_DUPLEX
                    cv2.putText(frame, f"{info['name']} ({info['nim']})", (left + 6, bottom - 6), font, 0.5, (255, 255, 255), 1)

                    if info["nim"] != "Unknown":
                        self.mark_attendance(info, db_connection, marked_attendance)

                cv2.imshow(subject, frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        except KeyboardInterrupt:
            print("Aplikasi ditutup dengan aman.")

        finally:
            video_capture.release()
            cv2.destroyAllWindows()
            db_connection.close()

    def start_attendance_wrapper(self):
        selected_subject = self.combo_subject.get()
        if selected_subject:
            self.start_attendance(selected_subject)

    def get_current_time(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def main():
    root = tk.Tk()
    app = AttendanceApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
