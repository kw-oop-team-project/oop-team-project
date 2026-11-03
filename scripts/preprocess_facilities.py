"""원본 CSV를 정리하고 SportsFacility 객체 목록으로 변환한다.

프로젝트 루트에서 실행: python scripts/preprocess_facilities.py
"""

from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.sports_facility import SportsFacility

DATA_PATH = ROOT / "data" / "공공체육시설.csv"


def clean_text(value):
    """비어 있는 셀은 None, 나머지는 앞뒤 공백을 제거한 문자열로 바꾼다."""
    if pd.isna(value):
        return None
    text = str(value).strip().replace("\n", " ")
    return text if text else None


def load_and_clean(path=DATA_PATH):
    """CSV → 열 통합 → 결측치 처리 → 숫자 변환 → DataFrame."""
    df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = df.columns.str.strip()

    # 원본 CSV의 자치구 명칭은 두 컬럼에 나뉘어 있다.
    district = df["시군구"].combine_first(df["시ㆍ군ㆍ구"])
    df["자치구"] = district.map(clean_text)

    for column in ["시설명", "시설종류", "소유기관", "관리주체"]:
        df[column] = df[column].map(clean_text)

    # 면적은 쉼표나 단위가 섞일 수 있으므로 숫자만 변환한다.
    area_text = df["부지면적"].astype("string").str.replace(",", "", regex=False)
    df["부지면적"] = pd.to_numeric(area_text, errors="coerce")

    # 자치구 및 시설명/종류가 없는 표 머리글·설명 행은 시설로 취급하지 않는다.
    valid_districts = {
        "종로구", "중구", "용산구", "성동구", "광진구", "동대문구", "중랑구",
        "성북구", "강북구", "도봉구", "노원구", "은평구", "서대문구",
        "마포구", "양천구", "강서구", "구로구", "금천구", "영등포구",
        "동작구", "관악구", "서초구", "강남구", "송파구", "강동구",
    }
    df = df[df["자치구"].isin(valid_districts) & df["시설명"].notna()
            & df["시설종류"].notna()].copy()
    return df.reset_index(drop=True)


def make_facilities(df):
    """정제된 DataFrame의 각 행을 SportsFacility 객체로 변환한다."""
    facilities = []
    for _, row in df.iterrows():
        area = None if pd.isna(row["부지면적"]) else float(row["부지면적"])
        facilities.append(SportsFacility(
            name=row["시설명"],
            district=row["자치구"],
            facility_type=row["시설종류"],
            owner=row["소유기관"],
            manager=row["관리주체"],
            area=area,
        ))
    return facilities


if __name__ == "__main__":
    cleaned = load_and_clean()
    facilities = make_facilities(cleaned)
    print(f"정제된 시설 수: {len(facilities)}개")
    print("첫 번째 시설:", facilities[0].get_info())
    print("상세정보 제공 여부:", facilities[0].has_detail())
    print("수영장 수:", sum(f.facility_type == "수영장" for f in facilities))
