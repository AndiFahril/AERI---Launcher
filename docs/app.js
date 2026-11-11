// GitHub Pages is hosted at https://OWNER.github.io/REPOSITORY/.
// Deriving this at runtime means the download link stays correct after a fork.
const pathParts = window.location.pathname.split('/').filter(Boolean);
const owner = window.location.hostname.split('.')[0];
const repository = pathParts[0] || 'AERI';
const githubBase = `https://github.com/${owner}/${repository}`;
const releasePage = `${githubBase}/releases/latest`;
const asset = `${releasePage}/download/AERI-Windows.zip`;

for (const id of ['source-link', 'footer-source']) {
  document.getElementById(id).href = githubBase;
}
document.getElementById('release-link').href = releasePage;
const download = document.getElementById('download-link');
download.href = asset;
document.getElementById('download-hint').textContent = 'Windows 10/11 · File ZIP · Instal tanpa administrator';
