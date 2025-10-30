def draw_annotations(chart_path, poi_range=None, bos_range=None, predicted=False):
    tag = "Predicted" if predicted else "True"
    return f"{tag} annotations would be drawn on {chart_path}"
