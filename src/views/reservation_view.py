"""선택 시설의 예약 일정과 공식 예약 링크를 표시한다."""

from .common import MISSING, get_ui, show_api_status


def show_reservations(result, *, ui=None):
    ui = get_ui(ui)
    ui.subheader("예약 안내")
    show_api_status(result, ui=ui)
    if not result.items:
        if result.state == "ok":
            ui.info(
                "확실하게 연결되는 예약 일정이 없습니다. 시설 홈페이지나 연락처로 문의해 주세요."
            )
        return
    ui.caption(
        "접수 상태와 기간은 제공기관 응답 기준입니다. 최종 예약 가능 여부는 공식 예약 페이지에서 확인하세요."
    )
    for reservation in result.items:
        with ui.container(border=True):
            ui.write(reservation.title or "예약 일정")
            ui.table(
                [
                    {"항목": "접수 상태", "내용": reservation.status or MISSING},
                    {
                        "항목": "장소 / 종목",
                        "내용": f"{reservation.place} / {reservation.sport}",
                    },
                    {
                        "항목": "접수 기간",
                        "내용": f"{reservation.receipt_start or MISSING} ~ {reservation.receipt_end or MISSING}",
                    },
                    {
                        "항목": "이용 기간",
                        "내용": f"{reservation.use_start or MISSING} ~ {reservation.use_end or MISSING}",
                    },
                    {"항목": "요금 안내", "내용": reservation.fee or MISSING},
                    {"항목": "문의", "내용": reservation.phone or MISSING},
                ]
            )
            if reservation.url:
                ui.link_button("공식 예약 페이지", reservation.url)
            else:
                ui.caption("유효한 공식 예약 링크가 제공되지 않았습니다.")
