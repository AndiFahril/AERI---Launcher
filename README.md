# AERI

> Personal Windows launcher dengan panel acrylic dan tata letak presisi 4 × 3.

## Unduh dan rilis publik

Rilis publik tersedia melalui halaman **Releases** GitHub. Pengguna cukup mengunduh `AERI-Windows.zip`, mengekstraknya, lalu menjalankan `PASANG.cmd`. Situs unduhan statis ada di folder `docs/` dan akan dipublikasikan otomatis oleh GitHub Pages setelah workflow Pages diaktifkan.

Untuk maintainer, lihat [PUBLISHING.md](PUBLISHING.md). Proyek telah menyertakan workflow build/rilis dan workflow GitHub Pages; tidak ada EXE yang perlu di-commit ke repository.

Launcher Windows dengan panel dark glass tetap 5%, logo AERI biru, dan halaman aplikasi 4 × 3.

## Memasang pembaruan

1. Tutup AERI versi lama melalui ikon tray → Keluar. Tombol × pada panel hanya menyembunyikan launcher.
2. Ekstrak seluruh AERI.zip, lalu jalankan PASANG.cmd dalam folder AERI.
3. Buka shortcut AERI di Desktop. Untuk versi portable, jalankan AERI.exe dari folder hasil ekstrak.

Pemasangan memperbarui EXE serta ikon tanpa menimpa apps.json, settings.json, atau ikon khusus yang sudah tersimpan. Jika EXE lama masih digunakan, aplikasi menampilkan petunjuk untuk menutupnya. Tidak perlu hak administrator. Simpan cadangan konfigurasi Anda sebelum memindahkan folder aplikasi.

## Halaman aplikasi

Satu halaman menampung maksimal 12 kartu dalam 4 kolom × 3 baris. Layar utama tidak memakai scrollbar vertikal. Halaman tambahan dibuat otomatis saat jumlah aplikasi melebihi 12.

- Geser mendatar pada kartu atau ruang kosong untuk berpindah satu halaman.
- Gestur touchpad atau roda mouse berpindah per halaman, dengan jeda untuk mencegah satu gestur melompati beberapa halaman.
- Gunakan tombol ‹ / › di bawah, Ctrl+← / Ctrl+→, atau PageUp / PageDown saat fokus tidak berada dalam kolom isian.
- Pencarian dan filter kategori mencari seluruh halaman. Perubahan pencarian/filter kembali ke halaman pertama.

Kartu berukuran tinggi 120 px dengan grid presisi 4 kolom × 3 baris. Ruang antar-kartu 14 px dan margin grid 2 px; pembagian sisa piksel dilakukan dari kiri ke kanan agar tidak ada kolom setengah piksel. Logo memakai area 40×40 dengan gambar maksimal 36×36, tetap proporsional dan terpusat. Nama berada di bawah logo; tombol edit berada di kanan bawah, dan kotak tombol cepat di kanan atas. Nama panjang memakai elipsis dan dapat dibaca lengkap lewat tooltip.

## Mengatur urutan

Klik Atur posisi. Seret baris aplikasi atau gunakan Naik / Turun, lalu Simpan. Urutan ini berlaku untuk seluruh aplikasi dan tetap tersimpan setelah launcher ditutup. Baris 1–12 mengisi halaman pertama, 13–24 halaman kedua, dan seterusnya. Batal menutup popup tanpa menyimpan perubahan.

## Menambah aplikasi dan aplikasi web Chrome

Klik + Tambah shortcut → Jenis: Aplikasi → Pilih aplikasi terpasang…. Cari aplikasi yang ingin dimasukkan, pilih Gunakan, tentukan tombol cepat/kategori, lalu Simpan. Daftar membaca shortcut Start Menu dan Desktop serta aplikasi Windows Store yang tersedia pada sesi pengguna.

Drive, Pinterest, atau aplikasi web Chrome yang sudah dipasang: pilih shortcut .lnk aslinya. AERI membuka shortcut tersebut agar pengaturan mode aplikasi dan profil Chrome tetap dipakai. Biarkan Argumen kosong untuk .lnk / .url. Simpan shortcut di folder tetap; jangan menghapus atau memindahkannya setelah ditambahkan.

Visual Studio Code dapat dipilih dari daftar aplikasi terpasang atau file Code.exe / shortcut-nya. ChatGPT dapat dipilih bila Windows menyediakan entri aplikasinya. Jika suatu aplikasi tidak muncul, gunakan tombol Pilih… untuk memilih file .exe / .lnk / .url sendiri. Anda juga dapat memilih Jenis: Website untuk URL http/https yang dibuka melalui browser default.

Ikon diambil dari target/shortcut. Ikon khusus dapat dipilih sendiri dan disalin ke folder icons. Aplikasi Store menggunakan logo paket bila bisa dibaca; jika tidak, inisial nama ditampilkan sampai Anda memilih ikon khusus.

## Keyboard dan tray

Kombinasi pembuka mengikuti settings.json; paket mempertahankan Ctrl+Space dari konfigurasi sebelumnya. Ubah melalui tombol roda gigi. Jika kombinasi sudah dipakai aplikasi lain, pilih kombinasi lain. AERI harus tetap berjalan di tray agar tombol global bekerja. Opsi Jalankan saat masuk Windows tersedia dalam pengaturan dan tidak diaktifkan secara otomatis.

| Tombol | Fungsi |
| --- | --- |
| Ctrl+F atau / | Fokus pencarian |
| Enter di pencarian | Membuka hasil pertama |
| Ctrl+N | Tambah shortcut |
| Ctrl+, | Pengaturan tombol global |
| Ctrl+R | Muat ulang konfigurasi |
| Ctrl+← / Ctrl+→, PageUp / PageDown | Halaman sebelumnya/berikutnya |
| Esc | Keluar dari pencarian, lalu menyembunyikan panel |

Tombol cepat setiap aplikasi bekerja dari seluruh halaman ketika launcher aktif dan Anda tidak sedang mengetik dalam kolom isian. Setelah target berhasil dibuka, launcher menyembunyikan diri. Pilih Keluar pada menu tray untuk menghentikan proses sepenuhnya.

## Data dan source

apps.json, settings.json, dan folder icons disimpan di samping EXE. Penyimpanan shortcut memakai file sementara dan penggantian atomik; backup terakhir ada pada apps.json.bak. Kepekatan panel tetap 5% tanpa slider; tint material native juga dikurangi agar wallpaper lebih terlihat. Mekanisme DWM/acrylic tetap digunakan dan teks/ikon tidak dibuat transparan.

## Membuka aplikasi yang sudah berjalan

AERI mendahulukan jendela aplikasi yang sesuai sebelum menjalankan target baru. Jendela yang diminimalkan dipulihkan. Chrome dibedakan berdasarkan profil dan identitas app web, bukan hanya nama proses chrome.exe. Shortcut .lnk dibaca untuk mengetahui target, argumen, dan identitas aplikasinya. Folder Explorer, aplikasi Store, dan protokol aplikasi juga diperiksa. Klik berulang saat aplikasi baru mulai tidak langsung meluncurkan proses kedua.

Untuk tab website biasa, AERI hanya memakai ulang halaman aktif yang dapat dikenali. Tab yang berada di belakang atau URL akun tertentu tidak selalu dapat diidentifikasi melalui jendela Windows; dalam kasus itu target tetap dibuka dengan mekanisme aslinya. Target berparameter yang identitas jendelanya tidak bisa dipastikan juga mengikuti perilaku aplikasi asal, agar profil/akun/dokumen yang salah tidak dipilih. Jika Windows menolak pemindahan fokus pada jendela yang ditemukan, AERI memberi pesan tanpa membuka duplikat.

Source Python disertakan. Pasang requirements.txt dengan Python 3.11+, jalankan python main.py. Build Windows: python -m PyInstaller AERI.spec. Pengujian: python tests/test_launcher.py. Tes menggunakan folder sementara, bukan konfigurasi pengguna.
