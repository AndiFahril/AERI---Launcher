# Mempublikasikan AERI

## Sekali saja: buat repository dan Pages

1. Buat repository publik baru bernama `AERI` di GitHub. Jangan pilih README, `.gitignore`, atau lisensi saat membuatnya karena folder ini sudah memilikinya.
2. Salin seluruh isi proyek ini ke folder repository, lalu jalankan:

   ```powershell
   git init
   git add .
   git commit -m "Prepare AERI 1.3.0"
   git branch -M main
   git remote add origin https://github.com/USERNAME/AERI.git
   git push -u origin main
   ```

3. Buka **Settings → Pages → Build and deployment**, pilih **GitHub Actions** sebagai Source. Workflow `Publish download site` akan membuat halaman di `https://USERNAME.github.io/AERI/`.

## Menerbitkan file unduhan

1. Pastikan `version_info.txt` dan catatan rilis sudah sesuai.
2. Buat dan push tag versi:

   ```powershell
   git tag v1.3.0
   git push origin v1.3.0
   ```

3. Workflow **Build Windows release** akan memasang dependency, menjalankan tes, membangun `AERI.exe`, membuat `AERI-Windows.zip`, lalu melampirkannya ke GitHub Release otomatis.
4. Situs unduhan akan selalu mengarah ke aset `AERI-Windows.zip` dari release terbaru. Tidak ada URL yang perlu diedit, bahkan setelah repository di-fork.

## Pemeriksaan sebelum tag

- Jalankan `python -m pip install -r requirements.txt`.
- Jalankan `python tests/test_launcher.py`.
- Jalankan `python -m PyInstaller --noconfirm --clean AERI.spec`.
- Jalankan `./tools/package_release.ps1 -Version 1.3.0` di PowerShell.
- Ekstrak `release/AERI-Windows.zip`, lalu uji `AERI.exe` dan `PASANG.cmd` pada Windows 10/11.

## Catatan keamanan

`apps.json` contoh dapat memuat path lokal. Jangan commit konfigurasi pribadi, token, atau data sensitif Anda. Pengguna akhir sebaiknya mengatur daftar aplikasi mereka sendiri sesudah instalasi.
