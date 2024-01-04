#!/usr/bin/env python3
"""Harcama Takipçisi — harcamaları komut satırından kaydeder ve özetler.

Kullanım:
    python harcama.py ekle 120 market haftalık alışveriş
    python harcama.py liste --ay 2024-02
    python harcama.py ozet
    python harcama.py sil 3
    python harcama.py disa-aktar harcamalar.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

VARSAYILAN_DOSYA = Path.home() / ".harcamalar.json"
CUBUK_GENISLIGI = 20


# --- Veri dosyası ------------------------------------------------------------

def veri_dosyasi(yol: str | None = None) -> Path:
    return Path(yol or os.environ.get("HARCAMA_DOSYA") or VARSAYILAN_DOSYA)


def yukle(yol: Path) -> list[dict]:
    if not yol.exists():
        return []
    with open(yol, encoding="utf-8") as f:
        return json.load(f)


def kaydet(yol: Path, kayitlar: list[dict]) -> None:
    """Önce geçici dosyaya yazar, sonra yerine koyar; yarıda kesilirse veri bozulmaz."""
    yol.parent.mkdir(parents=True, exist_ok=True)
    gecici = yol.with_name(yol.name + ".tmp")
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(kayitlar, f, ensure_ascii=False, indent=2)
    os.replace(gecici, yol)


# --- Girdi ayrıştırma --------------------------------------------------------

def tutar_coz(metin: str) -> float:
    """'120', '120,50', '120.50', '1.250,75' ve '45 TL' biçimlerini kabul eder."""
    m = metin.strip().replace(" ", "").replace("₺", "")
    if m.upper().endswith("TL"):
        m = m[:-2]
    if "," in m or re.fullmatch(r"\d{1,3}(\.\d{3})+", m):  # 1.250 → bin iki yüz elli
        m = m.replace(".", "").replace(",", ".")
    try:
        tutar = float(m)
    except ValueError:
        raise ValueError(f"Geçersiz tutar: {metin!r}") from None
    if not math.isfinite(tutar) or tutar <= 0:
        raise ValueError("Tutar sıfırdan büyük olmalı.")
    return round(tutar, 2)


def kategori_duzelt(ad: str) -> str:
    """Kategori adını Türkçe kurallarına uygun küçük harfe çevirir (MARKET → market, İLAÇ → ilaç)."""
    ad = ad.strip().replace("I", "ı").replace("İ", "i").lower()
    if not ad:
        raise ValueError("Kategori boş olamaz.")
    return ad


def tarih_coz(metin: str) -> date:
    try:
        return date.fromisoformat(metin)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Tarih YYYY-AA-GG biçiminde olmalı: {metin}") from None


def ay_coz(metin: str) -> str:
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", metin):
        raise argparse.ArgumentTypeError(f"Ay YYYY-AA biçiminde olmalı: {metin}")
    return metin


# --- İşlemler ----------------------------------------------------------------

def harcama_ekle(kayitlar: list[dict], tutar: float, kategori: str,
                 aciklama: str = "", tarih: date | None = None) -> dict:
    kayit = {
        "id": max((k["id"] for k in kayitlar), default=0) + 1,
        "tarih": (tarih or date.today()).isoformat(),
        "tutar": tutar,
        "kategori": kategori_duzelt(kategori),
        "aciklama": aciklama.strip(),
    }
    kayitlar.append(kayit)
    return kayit


def harcama_sil(kayitlar: list[dict], kimlik: int) -> dict:
    for i, kayit in enumerate(kayitlar):
        if kayit["id"] == kimlik:
            return kayitlar.pop(i)
    raise KeyError(f"{kimlik} numaralı harcama bulunamadı.")


def suz(kayitlar: list[dict], ay: str | None = None, kategori: str | None = None) -> list[dict]:
    sonuc = kayitlar
    if ay:
        sonuc = [k for k in sonuc if k["tarih"].startswith(ay)]
    if kategori:
        kategori = kategori_duzelt(kategori)
        sonuc = [k for k in sonuc if k["kategori"] == kategori]
    return sorted(sonuc, key=lambda k: (k["tarih"], k["id"]))


def kategori_ozeti(kayitlar: list[dict]) -> list[tuple[str, float]]:
    """Kategorileri toplam harcamaya göre büyükten küçüğe sıralar."""
    toplamlar: dict[str, float] = defaultdict(float)
    for k in kayitlar:
        toplamlar[k["kategori"]] += k["tutar"]
    return sorted(((ad, round(t, 2)) for ad, t in toplamlar.items()), key=lambda x: (-x[1], x[0]))


def aylik_ozet(kayitlar: list[dict]) -> list[tuple[str, float]]:
    toplamlar: dict[str, float] = defaultdict(float)
    for k in kayitlar:
        toplamlar[k["tarih"][:7]] += k["tutar"]
    return sorted((ay, round(t, 2)) for ay, t in toplamlar.items())


def csv_disa_aktar(kayitlar: list[dict], yol: Path) -> None:
    """Excel'in Türkçe ayarlarında doğrudan açılabilecek CSV yazar (; ayırıcı, virgüllü ondalık)."""
    with open(yol, "w", encoding="utf-8-sig", newline="") as f:
        yazici = csv.writer(f, delimiter=";")
        yazici.writerow(["id", "tarih", "tutar", "kategori", "aciklama"])
        for k in kayitlar:
            yazici.writerow([k["id"], k["tarih"], f"{k['tutar']:.2f}".replace(".", ","),
                             k["kategori"], k["aciklama"]])


# --- Çıktı -------------------------------------------------------------------

def tl(tutar: float) -> str:
    """1250.5 → '1.250,50 TL'"""
    return f"{tutar:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".") + " TL"


def cubuk(deger: float, en_buyuk: float) -> str:
    if en_buyuk <= 0:
        return ""
    return "█" * max(1, round(CUBUK_GENISLIGI * deger / en_buyuk))


def liste_yazdir(kayitlar: list[dict]) -> None:
    if not kayitlar:
        print("Kayıtlı harcama yok.")
        return
    gen = max(8, *(len(k["kategori"]) for k in kayitlar))
    print(f"{'#':>4}  {'Tarih':<10}  {'Kategori':<{gen}}  {'Tutar':>14}  Açıklama")
    for k in kayitlar:
        print(f"{k['id']:>4}  {k['tarih']:<10}  {k['kategori']:<{gen}}  {tl(k['tutar']):>14}  {k['aciklama']}")
    print(f"\n{len(kayitlar)} harcama, toplam {tl(sum(k['tutar'] for k in kayitlar))}")


def ozet_yazdir(kayitlar: list[dict], ay: str | None) -> None:
    if not kayitlar:
        print("Bu dönemde harcama yok.")
        return
    toplam = sum(k["tutar"] for k in kayitlar)
    print(f"{ay or 'Tüm zamanlar'} — toplam {tl(toplam)}\n")

    kategoriler = kategori_ozeti(kayitlar)
    gen = max(len(ad) for ad, _ in kategoriler)
    for ad, t in kategoriler:
        print(f"  {ad:<{gen}}  {cubuk(t, kategoriler[0][1]):<{CUBUK_GENISLIGI}}  {tl(t):>14}  %{100 * t / toplam:.0f}")

    if not ay:
        aylar = aylik_ozet(kayitlar)
        if len(aylar) > 1:
            en_buyuk = max(t for _, t in aylar)
            print("\nAylara göre:")
            for a, t in aylar:
                print(f"  {a}  {cubuk(t, en_buyuk):<{CUBUK_GENISLIGI}}  {tl(t):>14}")


# --- Komut satırı ------------------------------------------------------------

def arguman_ayristirici() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="harcama", description="Harcamalarınızı kaydedin ve özetleyin.")
    p.add_argument("--dosya", help="Veri dosyası (varsayılan: ~/.harcamalar.json)")
    alt = p.add_subparsers(dest="komut", required=True)

    e = alt.add_parser("ekle", help="Yeni harcama ekle")
    e.add_argument("tutar", help="Örn: 120 veya 45,90")
    e.add_argument("kategori", help="Örn: market, ulaşım, fatura")
    e.add_argument("aciklama", nargs="*", help="İsteğe bağlı açıklama")
    e.add_argument("--tarih", type=tarih_coz, help="YYYY-AA-GG (varsayılan: bugün)")

    l = alt.add_parser("liste", help="Harcamaları listele")
    l.add_argument("--ay", type=ay_coz, help="YYYY-AA")
    l.add_argument("--kategori")

    o = alt.add_parser("ozet", help="Kategori ve aylara göre özet")
    o.add_argument("--ay", type=ay_coz, help="YYYY-AA")

    s = alt.add_parser("sil", help="Harcama sil")
    s.add_argument("id", type=int)

    d = alt.add_parser("disa-aktar", help="CSV dosyasına aktar")
    d.add_argument("csv_dosyasi")
    d.add_argument("--ay", type=ay_coz, help="YYYY-AA")
    return p


def main(argv: list[str] | None = None) -> int:
    args = arguman_ayristirici().parse_args(argv)
    yol = veri_dosyasi(args.dosya)
    try:
        kayitlar = yukle(yol)
    except (OSError, json.JSONDecodeError) as h:
        print(f"Veri dosyası okunamadı ({yol}): {h}", file=sys.stderr)
        return 1

    try:
        if args.komut == "ekle":
            kayit = harcama_ekle(kayitlar, tutar_coz(args.tutar), args.kategori,
                                 " ".join(args.aciklama), args.tarih)
            kaydet(yol, kayitlar)
            print(f"#{kayit['id']} eklendi: {tl(kayit['tutar'])} · {kayit['kategori']} · {kayit['tarih']}")
        elif args.komut == "liste":
            liste_yazdir(suz(kayitlar, args.ay, args.kategori))
        elif args.komut == "ozet":
            ozet_yazdir(suz(kayitlar, args.ay), args.ay)
        elif args.komut == "sil":
            kayit = harcama_sil(kayitlar, args.id)
            kaydet(yol, kayitlar)
            print(f"#{kayit['id']} silindi: {tl(kayit['tutar'])} · {kayit['kategori']}")
        elif args.komut == "disa-aktar":
            secilen = suz(kayitlar, args.ay)
            csv_disa_aktar(secilen, Path(args.csv_dosyasi))
            print(f"{len(secilen)} harcama {args.csv_dosyasi} dosyasına aktarıldı.")
    except (ValueError, KeyError) as h:
        print(f"Hata: {h.args[0] if h.args else h}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
