# Pemeriksaan AERI 1.3

54 pengujian dijalankan: 53 lulus, 1 dilewati karena sandbox menolak registrasi hotkey Windows (error 5). Pengujian identitas dan enumerasi jendela native berhasil; pengujian pemilihan aplikasi dan aktivasi sebagian besar memakai mock agar tidak mengganggu aplikasi pengguna.

Pemeriksaan terbaru mencakup penggunaan ulang jendela EXE, profil Chrome, PWA melalui .lnk, URL akun dengan metadata tepat, aplikasi Store/protokol, folder Explorer, jendela yang diminimalkan, kegagalan aktivasi tanpa duplikat, cache jendela yang kadaluarsa, dan klik berulang saat startup. Identitas jendela native diuji pada jendela milik tes sendiri. Sebagian besar skenario aplikasi diuji dengan snapshot jendela dan aktivasi yang dimock agar tidak mengganggu aplikasi pengguna.

- Pembagian 0, 1, 12, 13, 24, dan 25 aplikasi; 4 kolom × 3 baris, tanpa scrollbar vertikal utama.
- Kartu tetap di dalam panel pada ukuran minimum 800×600. Lebar kolom konsisten pada halaman penuh maupun parsial.
- Animasi horizontal, batas halaman, satu gestur roda mouse satu halaman, dan swipe tidak menjalankan aplikasi secara tidak sengaja.
- Pencarian/filter lintas halaman; kembali ke halaman pertama ketika query berubah.
- Urutan melintasi batas halaman, penyimpanan ulang, dan penanganan kegagalan simpan tanpa mengganti konfigurasi lama.
- Pemilih aplikasi dengan worker latar belakang, pemilihan shortcut, parser identitas Store, validasi target, dan pembukaan .lnk lewat Windows Shell.
- Edit/tambah/hapus, ikon khusus, normalisasi logo, tombol lokal, registrasi hotkey Windows dan pemrosesan pesannya, rollback pengaturan, shortcut Windows, dan installer yang menjaga konfigurasi.
- Alpha panel 13/255 (5%) pada panel/popup dan tidak menumpuk saat repaint. Alpha tint acrylic native dikurangi dari 35/255 menjadi 20/255; blur tetap melalui DWM/acrylic.

Render main 12 kartu, halaman parsial, popup urutan, dan editor diperiksa. Contoh tambahan dalam render hanya berada di memori dan tidak disimpan sebagai aplikasi bawaan.

Rilis 1.3.0 menstandarkan geometri visual: panel minimum 800×600, margin 32 px, grid 4×3 dengan kartu 120 px dan gap 14 px. Build EXE baru perlu dijalankan pada Windows dengan Python 3.11+ sebelum tag rilis dibuat. Uji startup EXE otomatis pada lingkungan saat ini terhalang karena Python tidak tersedia; startup pada sesi desktop normal serta interaksi dengan seluruh aplikasi pengguna perlu diverifikasi langsung.

Pemindaian lokal menemukan 145 entri shortcut, termasuk Google Drive, Pinterest, dan Visual Studio Code. Daftar Store pada sesi alat tidak menyediakan entri; enumerasi Store pada sesi desktop pengguna tetap bergantung pada Windows. Tidak semua aplikasi pengguna dibuka dalam pengujian; target dan profil Chrome yang tersedia pada komputer pengguna mengikuti file shortcut masing-masing.
