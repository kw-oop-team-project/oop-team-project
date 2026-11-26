from PIL import Image, ImageDraw
from io import BytesIO
import base64

# 원형 그래프를 생성하는 클래스

class FacilityChart:
    TOP_N = 5

    COLORS = (
        "#2563eb",
        "#14b8a6",
        "#f59e0b",
        "#8b5cf6",
        "#ef4444",
        "#9ca3af"
    )

    def create_pie_chart(self, counts):
        total = sum(counts.values())

        if total == 0:
            return None

        image = Image.new("RGB", (400, 400), "white")
        draw = ImageDraw.Draw(image)

        start = -90

        for i, (kind, count) in enumerate(counts.items()):
            angle = count / total * 360

            draw.pieslice(
                (10, 10, 390, 390),
                start=start,
                end=start + angle,
                fill=self.COLORS[i % len(self.COLORS)]
            )

            start += angle

        image = image.resize(
            (150, 150), Image.Resampling.LANCZOS
        )

        buffer = BytesIO()
        image.save(buffer, format="PNG")

        encoded = base64.b64encode(
            buffer.getvalue()
        ).decode("ascii")

        return "data:image/png;base64," + encoded