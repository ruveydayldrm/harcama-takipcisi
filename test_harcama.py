import contextlib
import io
import tempfile
import unittest
from datetime import date
from pathlib import Path

import harcama


class TutarCozTesti(unittest.TestCase):
    def test_gecerli_bicimler(self):
        self.assertEqual(harcama.tutar_coz("120"), 120.0)
        self.assertEqual(harcama.tutar_coz("45,90"), 45.9)
        self.assertEqual(harcama.tutar_coz("45.90"), 45.9)
        self.assertEqual(harcama.tutar_coz("1.250,75"), 1250.75)
        self.assertEqual(harcama.tutar_coz("1.250"), 1250.0)
        self.assertEqual(harcama.tutar_coz("12.5"), 12.5)
        self.assertEqual(harcama.tutar_coz("80 TL"), 80.0)

    def test_gecersiz_tutarlar(self):
        for metin in ["abc", "0", "-5", "nan", "inf", ""]:
            with self.subTest(metin=metin), self.assertRaises(ValueError):
                harcama.tutar_coz(metin)


class IslemTesti(unittest.TestCase):
    def setUp(self):
        self.kayitlar = []
        harcama.harcama_ekle(self.kayitlar, 100, "Market", tarih=date(2024, 2, 10))
        harcama.harcama_ekle(self.kayitlar, 50, "ULAŞIM", "otobüs", date(2024, 2, 11))
        harcama.harcama_ekle(self.kayitlar, 30, "market", tarih=date(2024, 3, 1))

    def test_kategori_turkce_kucuk_harf(self):
        self.assertEqual(harcama.kategori_duzelt("İLAÇ"), "ilaç")
        self.assertEqual(harcama.kategori_duzelt("  KIRTASİYE "), "kırtasiye")
        self.assertEqual(self.kayitlar[1]["kategori"], "ulaşım")

    def test_silinen_numara_tekrar_kullanilmaz(self):
        harcama.harcama_sil(self.kayitlar, 2)
        yeni = harcama.harcama_ekle(self.kayitlar, 10, "kafe")
        self.assertEqual(yeni["id"], 4)

    def test_olmayan_kayit_silinemez(self):
        with self.assertRaises(KeyError):
            harcama.harcama_sil(self.kayitlar, 99)

    def test_aya_ve_kategoriye_gore_suzme(self):
        self.assertEqual([k["id"] for k in harcama.suz(self.kayitlar, ay="2024-02")], [1, 2])
        self.assertEqual([k["id"] for k in harcama.suz(self.kayitlar, kategori="MARKET")], [1, 3])

    def test_ozetler(self):
        self.assertEqual(harcama.kategori_ozeti(self.kayitlar), [("market", 130.0), ("ulaşım", 50.0)])
        self.assertEqual(harcama.aylik_ozet(self.kayitlar), [("2024-02", 150.0), ("2024-03", 30.0)])

    def test_tl_bicimi(self):
        self.assertEqual(harcama.tl(1250.5), "1.250,50 TL")
        self.assertEqual(harcama.tl(7), "7,00 TL")


class KomutSatiriTesti(unittest.TestCase):
    def setUp(self):
        self.klasor = tempfile.TemporaryDirectory()
        self.dosya = Path(self.klasor.name) / "veri.json"

    def tearDown(self):
        self.klasor.cleanup()

    def calistir(self, *argumanlar):
        cikti = io.StringIO()
        with contextlib.redirect_stdout(cikti), contextlib.redirect_stderr(cikti):
            kod = harcama.main(["--dosya", str(self.dosya), *argumanlar])
        return kod, cikti.getvalue()

    def test_ekle_ozet_ve_csv(self):
        self.assertEqual(self.calistir("ekle", "120,5", "market", "haftalık", "--tarih", "2024-02-10")[0], 0)
        self.assertEqual(self.calistir("ekle", "30", "kafe", "--tarih", "2024-02-12")[0], 0)

        kod, cikti = self.calistir("ozet", "--ay", "2024-02")
        self.assertEqual(kod, 0)
        self.assertIn("150,50 TL", cikti)
        self.assertIn("market", cikti)

        csv_yolu = Path(self.klasor.name) / "cikti.csv"
        self.calistir("disa-aktar", str(csv_yolu))
        satirlar = csv_yolu.read_text(encoding="utf-8-sig").splitlines()
        self.assertEqual(satirlar[1], "1;2024-02-10;120,50;market;haftalık")

    def test_hatali_tutar_kayit_olusturmaz(self):
        kod, cikti = self.calistir("ekle", "bedava", "market")
        self.assertEqual(kod, 1)
        self.assertIn("Geçersiz tutar", cikti)
        self.assertFalse(self.dosya.exists())


if __name__ == "__main__":
    unittest.main()
