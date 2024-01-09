# Harcama Takipçisi 💸

Harcamalarınızı komut satırından hızlıca kaydeden, aylık ve kategori bazlı özet çıkaran küçük bir Python aracı.

## Özellikler

- Tek satırda kayıt: `python harcama.py ekle 120 market`
- Türkçe tutar biçimleri: `120`, `45,90`, `1.250,75`, `80 TL`
- Kategori ve aylara göre özet, çubuk grafiklerle
- Excel'de doğrudan açılan CSV dışa aktarma (`;` ayırıcı, virgüllü ondalık)
- Veriler `~/.harcamalar.json` dosyasında tutulur; yazma sırasında kesilse bile bozulmaz
- Ek kütüphane gerektirmez; yalnızca Python 3.9+

## Kullanım

```bash
python harcama.py ekle 120 market haftalık alışveriş
python harcama.py ekle "45,90" ulaşım --tarih 2024-02-10   # PowerShell'de virgüllü tutarı tırnağa alın
python harcama.py liste --ay 2024-02
python harcama.py liste --kategori market
python harcama.py ozet
python harcama.py ozet --ay 2024-02
python harcama.py sil 3
python harcama.py disa-aktar subat.csv --ay 2024-02
```

Örnek özet:

```
2024-02 — toplam 1.250,00 TL

  market  ████████████████████      800,00 TL  %64
  ulaşım  ██████                    250,00 TL  %20
  kafe    █████                     200,00 TL  %16
```

Farklı bir veri dosyası kullanmak için `--dosya yol.json` ya da `HARCAMA_DOSYA` ortam değişkenini kullanabilirsiniz.

## Testler

```bash
python -m unittest -v
```
