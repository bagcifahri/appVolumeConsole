# Uygulama Ses Konsolu (NVDA eklentisi)

[English](README.md)

Windows'ta ses kullanan uygulamaların ses düzeyini, sessiz durumunu, giriş ve çıkış aygıtlarını tek bir komut katmanından yönetir.

## Kullanım

Konsolu açmak için **NVDA+Windows+S** tuşlarına basın. Kısayolu NVDA menüsü > Tercihler > Girdi hareketleri > "Uygulama Ses Konsolu" bölümünden değiştirebilirsiniz.

| Tuş | İşlev |
| --- | --- |
| Sağ / sol ok | Sonraki / önceki uygulama |
| Home / End | İlk / son uygulama |
| Yukarı / aşağı ok | Ses düzeyini artır / azalt |
| M | Sesi kapat / aç |
| Alt + yukarı / aşağı ok | Çıkış aygıtını değiştir |
| Ctrl + yukarı / aşağı ok | Giriş aygıtını değiştir |
| Boşluk | Geçerli uygulamayı yeniden oku |
| F1 | Komutların listesi |
| Esc | Konsolu kapat |

Bu tuşlar dışında bir tuşa basarsanız konsol kısa bir bip sesiyle kapanır. Başka bir pencere öne geldiğinde de konsol kapanır.

Her uygulama "ad, ses düzeyi (sessizse "sessiz"), çıkış aygıtı, giriş aygıtı" biçiminde okunur. Uygulama Windows varsayılan aygıtını kullanıyorsa "varsayılan (aygıt adı)" denir. Aygıt listesinin başında "varsayılan" seçeneği vardır. Bu seçenek uygulamayı yeniden Windows'un varsayılan aygıtına bağlar.

## Ayarlar

NVDA ayarlarındaki "Uygulama Ses Konsolu" kategorisinde şunlar bulunur:

- **Konsol açıldığında şuradan başla:** odaktaki uygulama (varsayılan) veya listedeki ilk uygulama.
- **Ses adımı:** ok tuşlarıyla ses düzeyinin yüzde kaç değişeceği (1 ile 25 arası, varsayılan 5).

## Notlar

- Liste, Windows Ses Karıştırıcısı'nda görünen uygulamalardan oluşur. Ses oturumu açmamış bir uygulama listede yer almaz. Tek istisna, konsolu açtığınızda odakta olan uygulamadır: ses düzeyi henüz ayarlanamasa da aygıtı seçilebilir.
- Uygulama başına aygıt seçimi, Windows Ayarlar'daki "Uygulama ses düzeyi ve cihaz tercihleri" sayfasının kullandığı belgelenmemiş Windows arabirimiyle yapılır. Bazı uygulamalar yeni aygıta ancak sesi yeniden başlattıklarında geçer.

## Derleme

```
python build.py
```

Komut, `addon` klasöründen `appVolumeConsole-<sürüm>.nvda-addon` dosyasını oluşturur ve Türkçe çeviriyi de derler.

## Lisans

GNU Genel Kamu Lisansı, sürüm 2. Ayrıntılar için [COPYING.txt](COPYING.txt) dosyasına bakın.
