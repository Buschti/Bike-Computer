import math


def plot_path(ax, path, color='blue', linewidth=1):
    try:
        lats = [node.latitude for node in path]
        lons = [node.longitude for node in path]

        ax.scatter([path[0].longitude], [path[0].latitude], color='green', zorder=4, s=500)
        ax.scatter([path[-1].longitude], [path[-1].latitude], color='red', zorder=4, s=500)

        ax.plot(lons, lats, color=color, linewidth=linewidth, zorder=3)

        avg_lat = sum(lats) / len(lats)
        aspect_ratio = 1 / math.cos(math.radians(avg_lat))

        ax.set_aspect(aspect_ratio)
    except:
        print(f"Path: {path} is empty!")
