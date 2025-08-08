# Bike-Computer
Repository for my Bachelor's thesis:
Development and Optimization of a  Bike Computer with Navigation for  Embedded Systems

This is my Bachelor’s thesis project: a Raspberry Pi–based bicycle computer with built-in navigation. It calculates routes using OpenStreetMap data and shows directions on a small display. Everything’s coded in Python, with minimal libraries and a focus on making it work from scratch. Feel free to use or improve it however you like.

## Installation
```bash
git clone https://github.com/Buschti/Bike-Computer.git
cd Bike-Computer
python -m venv env
source env/bin/activate  # Linux/macOS
env\Scripts\activate     # Windows
pip install -r requirements.txt
```

## License
This project is licensed under the Unlicense. Use it however you want!

## Future Projects

Some ideas to build on this project:

- **Search Function**  
  Add a way to find places like stores or street names, and filter routes by surface type (like asphalt or gravel).

- **Smartphone Route Planning**  
  Let users plan trips on their phones (e.g. using Komoot), then send GPX files to the bike computer via Bluetooth.

- **Energy-Efficient Routing**  
  For e-bike users—calculate routes that save battery and show how much energy different paths use.
