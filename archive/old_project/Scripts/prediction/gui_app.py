"""
Simple GUI for AQI Prediction System
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from Scripts.prediction.generate_report import generate_report_to_string, aqi_category


class AQIPredictionGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("VAHAN - AQI Prediction System")
        self.root.geometry("650x750")
        self.root.resizable(True, True)
        
        # Set style
        self.root.configure(bg='#f0f0f0')
        
        # Title
        title_frame = tk.Frame(root, bg='#2c3e50', height=80)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame, 
            text="🌬️ VAHAN AQI PREDICTION SYSTEM", 
            font=('Arial', 18, 'bold'), 
            bg='#2c3e50', 
            fg='white'
        )
        title_label.pack(expand=True)
        
        # Main content frame
        main_frame = tk.Frame(root, bg='#f0f0f0', padx=30, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # Location Input
        location_label = tk.Label(
            main_frame, 
            text="📍 LOCATION", 
            font=('Arial', 12, 'bold'), 
            bg='#f0f0f0', 
            fg='#2c3e50'
        )
        location_label.pack(anchor='w', pady=(10, 5))
        
        coord_frame = tk.Frame(main_frame, bg='#f0f0f0')
        coord_frame.pack(fill='x')
        
        # Latitude
        lat_frame = tk.Frame(coord_frame, bg='#f0f0f0')
        lat_frame.pack(side='left', expand=True, fill='x', padx=(0, 10))
        
        tk.Label(lat_frame, text="Latitude (°N):", bg='#f0f0f0').pack(anchor='w')
        self.lat_entry = tk.Entry(lat_frame, font=('Arial', 11), width=15)
        self.lat_entry.pack(fill='x', pady=(2, 0))
        self.lat_entry.insert(0, "28.6139")  # Delhi default
        
        # Longitude
        lon_frame = tk.Frame(coord_frame, bg='#f0f0f0')
        lon_frame.pack(side='left', expand=True, fill='x')
        
        tk.Label(lon_frame, text="Longitude (°E):", bg='#f0f0f0').pack(anchor='w')
        self.lon_entry = tk.Entry(lon_frame, font=('Arial', 11), width=15)
        self.lon_entry.pack(fill='x', pady=(2, 0))
        self.lon_entry.insert(0, "77.2090")  # Delhi default
        
        # Quick location buttons
        quick_frame = tk.Frame(main_frame, bg='#f0f0f0')
        quick_frame.pack(fill='x', pady=(5, 10))
        
        cities = [
            ("Delhi", 28.6139, 77.2090),
            ("Mumbai", 19.0760, 72.8777),
            ("Chennai", 13.0827, 80.2707),
            ("Kolkata", 22.5726, 88.3639),
            ("Bengaluru", 12.9716, 77.5946),
        ]
        
        for city, lat, lon in cities:
            btn = tk.Button(
                quick_frame, 
                text=city, 
                command=lambda l=lat, lo=lon: self.set_location(l, lo),
                bg='#3498db', 
                fg='white',
                font=('Arial', 9),
                padx=8,
                pady=2
            )
            btn.pack(side='left', padx=2)
        
        # Time Period
        time_label = tk.Label(
            main_frame, 
            text="📅 TIME PERIOD", 
            font=('Arial', 12, 'bold'), 
            bg='#f0f0f0', 
            fg='#2c3e50'
        )
        time_label.pack(anchor='w', pady=(20, 5))
        
        time_frame = tk.Frame(main_frame, bg='#f0f0f0')
        time_frame.pack(fill='x')
        
        # Month
        month_frame = tk.Frame(time_frame, bg='#f0f0f0')
        month_frame.pack(side='left', expand=True, fill='x', padx=(0, 10))
        
        tk.Label(month_frame, text="Month:", bg='#f0f0f0').pack(anchor='w')
        self.month_var = tk.StringVar()
        month_combo = ttk.Combobox(
            month_frame, 
            textvariable=self.month_var,
            values=['1 - January', '2 - February', '3 - March', '4 - April',
                    '5 - May', '6 - June', '7 - July', '8 - August',
                    '9 - September', '10 - October', '11 - November', '12 - December'],
            state='readonly',
            width=18
        )
        month_combo.pack(fill='x', pady=(2, 0))
        month_combo.current(0)  # January default
        
        # Year
        year_frame = tk.Frame(time_frame, bg='#f0f0f0')
        year_frame.pack(side='left', expand=True, fill='x')
        
        tk.Label(year_frame, text="Year:", bg='#f0f0f0').pack(anchor='w')
        self.year_var = tk.StringVar()
        year_combo = ttk.Combobox(
            year_frame,
            textvariable=self.year_var,
            values=['2020', '2021', '2022', '2023', '2024'],
            state='readonly',
            width=10
        )
        year_combo.pack(fill='x', pady=(2, 0))
        year_combo.current(3)  # 2023 default
        
        # Horizon
        horizon_label = tk.Label(
            main_frame, 
            text="⏱️ PREDICTION HORIZON", 
            font=('Arial', 12, 'bold'), 
            bg='#f0f0f0', 
            fg='#2c3e50'
        )
        horizon_label.pack(anchor='w', pady=(20, 5))
        
        self.horizon_var = tk.StringVar(value="1 Month Climatology")
        horizon_options = [
            "15 Day Climatology",
            "1 Month Climatology",
            "3 Month Climatology",
            "6 Month Climatology",
            "1 Year Climatology"
        ]
        
        for option in horizon_options:
            tk.Radiobutton(
                main_frame,
                text=option,
                variable=self.horizon_var,
                value=option,
                bg='#f0f0f0',
                font=('Arial', 10)
            ).pack(anchor='w')
        
        # Predict Button
        predict_btn = tk.Button(
            main_frame,
            text="🔮 PREDICT AQI",
            command=self.predict_aqi,
            bg='#27ae60',
            fg='white',
            font=('Arial', 14, 'bold'),
            padx=20,
            pady=10
        )
        predict_btn.pack(pady=20)
        
        # Result Display
        result_label = tk.Label(
            main_frame,
            text="📋 PREDICTION REPORT",
            font=('Arial', 12, 'bold'),
            bg='#f0f0f0',
            fg='#2c3e50'
        )
        result_label.pack(anchor='w', pady=(10, 5))
        
        self.result_text = scrolledtext.ScrolledText(
            main_frame,
            wrap=tk.WORD,
            width=70,
            height=15,
            font=('Consolas', 9)
        )
        self.result_text.pack(fill='both', expand=True)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready. Enter location and time period.")
        status_bar = tk.Label(
            root,
            textvariable=self.status_var,
            bd=1,
            relief=tk.SUNKEN,
            anchor=tk.W,
            bg='#ecf0f1',
            font=('Arial', 9)
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def set_location(self, lat, lon):
        """Set location from quick select buttons."""
        self.lat_entry.delete(0, tk.END)
        self.lat_entry.insert(0, str(lat))
        self.lon_entry.delete(0, tk.END)
        self.lon_entry.insert(0, str(lon))
    
    def predict_aqi(self):
        """Run prediction and display results."""
        try:
            # Get inputs
            lat = float(self.lat_entry.get())
            lon = float(self.lon_entry.get())
            month = int(self.month_var.get().split(' - ')[0])
            year = int(self.year_var.get())
            horizon = self.horizon_var.get()
            
            # Validate
            if not (-90 <= lat <= 90):
                raise ValueError("Latitude must be between -90 and 90")
            if not (-180 <= lon <= 180):
                raise ValueError("Longitude must be between -180 and 180")
            
            # Update status
            self.status_var.set(f"Predicting AQI for {lat:.2f}°N, {lon:.2f}°E...")
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, "Loading... Please wait.\n")
            self.root.update()
            
            # Import here to avoid circular imports
            from Scripts.prediction.predict_aqi import predict_aqi as predict_aqi_func
            from Scripts.prediction.generate_report_1 import format_report_string, aqi_category
            
            # Run prediction
            result = predict_aqi_func(lat, lon, month, year)
            
            # Format report
            report = format_report_string(
                lat=lat,
                lon=lon,
                elevation=result['location']['elevation'],
                month=month,
                year=year,
                horizon_desc=horizon,
                final_aqi=result['final_aqi'],
                baseline_aqi=result['baseline_aqi'],
                spatial_effect=result['spatial_effect'],
                features=result['features'],
                wind_dir=result['wind_dir'],
                station_effects=result['station_effects']
            )
            
            # Display
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, report)
            
            # Update status
            category = aqi_category(result['final_aqi'])
            self.status_var.set(f"Prediction complete! AQI: {result['final_aqi']:.0f} ({category})")
            
        except ValueError as e:
            messagebox.showerror("Input Error", str(e))
            self.status_var.set("Error: Invalid input")
        except Exception as e:
            messagebox.showerror("Prediction Error", f"An error occurred:\n{str(e)}")
            self.status_var.set("Error: Prediction failed")


def main():
    root = tk.Tk()
    app = AQIPredictionGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()