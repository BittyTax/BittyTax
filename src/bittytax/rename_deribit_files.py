import os

directory = r"C:\Users\agarn\OneDrive\Documents\CryptoTax\2024_2025\Deribit"

for filename in os.listdir(directory):
    new_filename = filename.replace(" ", "_").replace(",", "_")
    if new_filename != filename:
        old_path = os.path.join(directory, filename)
        new_path = os.path.join(directory, new_filename)
        os.rename(old_path, new_path)
        print(f"Renamed: {filename} -> {new_filename}")