"""
Gerador automático de update.js e modpack.json
================================================
Escaneia os .jar na pasta do modpack (e na subpasta pojav, se existir)
e gera os arquivos no formato esperado pelo launcher.

Uso:
    python generate.py                          # usa versão padrão 1.0.0
    python generate.py --version 1.2.3          # define a versão do modpack
    python generate.py --base-url https://github.com/SEU_USER/REPO/raw/refs/heads/main
"""

import os
import sys
import json
import hashlib
import argparse

# ── Configurações padrão ────────────────────────────────────────────────────
DEFAULT_BASE_URL = "https://github.com/dbcbrasil/modpack/raw/refs/heads/main"
DEFAULT_VERSION = "1.0.0"

# Extensões de arquivo que serão consideradas mods
MOD_EXTENSIONS = {".jar"}

# Arquivos/pastas que devem ser ignorados ao escanear
IGNORED_FILES = {
    "generate.py",
    "modpack.json",
    "update.js",
    "options.txt",
    "optionsof.txt",
    "servers.dat",
}
IGNORED_DIRS = {"pojav", ".git", "__pycache__"}


# ── Utilitários ─────────────────────────────────────────────────────────────
def sha1_file(filepath: str) -> str:
    """Calcula o SHA-1 de um arquivo."""
    h = hashlib.sha1()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def collect_jars(directory: str) -> list[dict]:
    """
    Retorna uma lista de dicts com informações de cada .jar encontrado
    diretamente em `directory` (não recursivo).
    """
    jars = []
    for entry in sorted(os.listdir(directory)):
        if entry.lower() in {x.lower() for x in IGNORED_FILES}:
            continue
        full_path = os.path.join(directory, entry)
        if not os.path.isfile(full_path):
            continue
        _, ext = os.path.splitext(entry)
        if ext.lower() not in MOD_EXTENSIONS:
            continue
        jars.append({
            "name": entry,
            "path": full_path,
            "size": os.path.getsize(full_path),
            "sha1": sha1_file(full_path),
        })
    return jars


# ── Geradores ────────────────────────────────────────────────────────────────
def generate_update_js(jars: list[dict], base_url: str, version: str, subfolder: str = "") -> str:
    """
    Gera o conteúdo do update.js.

    Formato:
        versão|
        url_do_mod_1|
        url_do_mod_2|
        ...
    """
    url_prefix = f"{base_url}/{subfolder}" if subfolder else base_url
    lines = [f"{version}|"]
    for jar in jars:
        lines.append(f"{url_prefix}/{jar['name']}|")
    # Linha em branco no final
    lines.append("")
    return "\n".join(lines)


def generate_modpack_json(jars: list[dict], base_url: str) -> str:
    """
    Gera o conteúdo do modpack.json.

    Formato:
        {"mods": [
            {"name": "...", "downloadURL": "...", "size": 123, "sha1": "..."},
            ...
        ]}
    """
    mods = []
    for jar in jars:
        mods.append({
            "name": jar["name"],
            "downloadURL": f"{base_url}/{jar['name']}",
            "size": jar["size"],
            "sha1": jar["sha1"],
        })
    return json.dumps({"mods": mods}, ensure_ascii=False, separators=(",", ":"))


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Gera update.js e modpack.json a partir dos .jar presentes na pasta."
    )
    parser.add_argument(
        "--version", "-v",
        default=DEFAULT_VERSION,
        help=f"Versão do modpack (aparece no update.js). Padrão: {DEFAULT_VERSION}",
    )
    parser.add_argument(
        "--base-url", "-u",
        default=DEFAULT_BASE_URL,
        help=f"URL base do repositório GitHub. Padrão: {DEFAULT_BASE_URL}",
    )
    parser.add_argument(
        "--dir", "-d",
        default=os.path.dirname(os.path.abspath(__file__)),
        help="Diretório raiz do modpack. Padrão: pasta deste script.",
    )
    args = parser.parse_args()

    modpack_dir = args.dir
    base_url = args.base_url.rstrip("/")
    version = args.version

    # ── Pasta raiz ──────────────────────────────────────────────────────
    print(f"📂 Escaneando: {modpack_dir}")
    root_jars = collect_jars(modpack_dir)
    print(f"   Encontrados {len(root_jars)} mod(s) na raiz.")

    # update.js (raiz)
    update_js_path = os.path.join(modpack_dir, "update.js")
    update_js_content = generate_update_js(root_jars, base_url, version)
    with open(update_js_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(update_js_content)
    print(f"   ✅ {update_js_path}")

    # modpack.json
    modpack_json_path = os.path.join(modpack_dir, "modpack.json")
    modpack_json_content = generate_modpack_json(root_jars, base_url)
    with open(modpack_json_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(modpack_json_content)
    print(f"   ✅ {modpack_json_path}")

    # ── Subpasta pojav (se existir e tiver .jar) ───────────────────────
    pojav_dir = os.path.join(modpack_dir, "pojav")
    if os.path.isdir(pojav_dir):
        pojav_jars = collect_jars(pojav_dir)
        if pojav_jars:
            print(f"\n📂 Escaneando: {pojav_dir}")
            print(f"   Encontrados {len(pojav_jars)} mod(s) no pojav.")

            pojav_update_path = os.path.join(pojav_dir, "update.js")
            pojav_update_content = generate_update_js(
                pojav_jars, base_url, version, subfolder="pojav"
            )
            with open(pojav_update_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(pojav_update_content)
            print(f"   ✅ {pojav_update_path}")
        else:
            print(f"\n⚠️  Pasta pojav existe mas não contém .jar — update.js pojav não gerado.")

    # ── Resumo ──────────────────────────────────────────────────────────
    print("\n🎉 Geração concluída!")
    print(f"   Versão: {version}")
    print(f"   Base URL: {base_url}")
    print(f"   Mods (raiz): {len(root_jars)}")
    for jar in root_jars:
        print(f"      • {jar['name']}  ({jar['size']:,} bytes)  sha1={jar['sha1']}")


if __name__ == "__main__":
    main()


