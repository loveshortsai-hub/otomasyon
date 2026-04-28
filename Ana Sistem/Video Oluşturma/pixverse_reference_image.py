import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional


PIXVERSE_REFERENCE_MAX_SIDE = 1920


class ReferenceImagePreparationError(RuntimeError):
    pass


def _resolve_powershell() -> str:
    for candidate in ("powershell", "pwsh"):
        found = shutil.which(candidate)
        if found:
            return found
    raise ReferenceImagePreparationError("PowerShell bulunamadı.")


def _ps_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _run_powershell(script: str) -> str:
    result = subprocess.run(
        [_resolve_powershell(), "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "Bilinmeyen PowerShell hatası").strip()
        raise ReferenceImagePreparationError(detail.splitlines()[0][:240] if detail else "PowerShell komutu çalıştırılamadı.")
    return (result.stdout or "").strip()


def read_image_size(image_path: Path) -> tuple[int, int]:
    image_path = Path(image_path)
    script = (
        "Add-Type -AssemblyName System.Drawing; "
        f"$img = [System.Drawing.Image]::FromFile({_ps_literal(str(image_path))}); "
        "try { Write-Output ($img.Width.ToString() + 'x' + $img.Height.ToString()) } "
        "finally { $img.Dispose() }"
    )
    output = _run_powershell(script)
    match = re.search(r"(\d+)x(\d+)", output)
    if not match:
        raise ReferenceImagePreparationError("Referans görsel boyutu okunamadı.")
    return int(match.group(1)), int(match.group(2))


def _resize_image_to_jpeg(source_path: Path, target_path: Path, width: int, height: int):
    target_path.parent.mkdir(parents=True, exist_ok=True)
    script = (
        "Add-Type -AssemblyName System.Drawing; "
        f"$src = {_ps_literal(str(source_path))}; "
        f"$dst = {_ps_literal(str(target_path))}; "
        f"$newWidth = {int(width)}; "
        f"$newHeight = {int(height)}; "
        "$img = [System.Drawing.Image]::FromFile($src); "
        "try { "
        "  $bmp = New-Object System.Drawing.Bitmap($newWidth, $newHeight); "
        "  try { "
        "    $gfx = [System.Drawing.Graphics]::FromImage($bmp); "
        "    try { "
        "      $gfx.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality; "
        "      $gfx.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic; "
        "      $gfx.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality; "
        "      $gfx.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality; "
        "      $gfx.DrawImage($img, 0, 0, $newWidth, $newHeight); "
        "    } finally { $gfx.Dispose() } "
        "    $codec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | "
        "      Where-Object { $_.MimeType -eq 'image/jpeg' } | Select-Object -First 1; "
        "    if ($null -ne $codec) { "
        "      $encoder = [System.Drawing.Imaging.Encoder]::Quality; "
        "      $params = New-Object System.Drawing.Imaging.EncoderParameters(1); "
        "      try { "
        "        $params.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter($encoder, [long]92); "
        "        $bmp.Save($dst, $codec, $params); "
        "      } finally { $params.Dispose() } "
        "    } else { "
        "      $bmp.Save($dst, [System.Drawing.Imaging.ImageFormat]::Jpeg); "
        "    } "
        "  } finally { $bmp.Dispose() } "
        "} finally { $img.Dispose() }"
    )
    _run_powershell(script)


def prepare_reference_image_for_upload(
    reference_image: Optional[Path],
    output_dir: Path,
    max_side: int = PIXVERSE_REFERENCE_MAX_SIDE,
) -> Optional[Path]:
    if reference_image is None:
        return None

    source_path = Path(reference_image)
    if not source_path.exists():
        return source_path

    width, height = read_image_size(source_path)
    if width <= max_side and height <= max_side:
        return source_path

    scale = min(max_side / width, max_side / height)
    new_width = max(1, int(round(width * scale)))
    new_height = max(1, int(round(height * scale)))

    prepared_dir = Path(output_dir) / "_pixverse_input"
    prepared_path = prepared_dir / f"{source_path.stem}_pixverse_{new_width}x{new_height}.jpg"
    if prepared_path.exists():
        return prepared_path

    _resize_image_to_jpeg(source_path, prepared_path, new_width, new_height)
    return prepared_path
