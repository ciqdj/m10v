# Copyright (C) 2026 zhaoo and gr-custom-tool contributors
# SPDX-License-Identifier: GPL-2.0-only
"""One-request JSON bridge for the vendored GR IV editor core."""
from __future__ import annotations

import json
from pathlib import Path
import sys

MAX_REQUEST = 192 * 1024 * 1024


def confined(root, value, *, must_exist=False, kind="file"):
    root = Path(root).resolve(strict=True)
    candidate = Path(value)
    if not candidate.is_absolute():
        raise ValueError("path must be absolute")
    candidate = candidate.resolve(strict=must_exist)
    if root != candidate and root not in candidate.parents:
        raise ValueError("path escapes workspace")
    if must_exist and candidate.is_symlink():
        raise ValueError("path must not be a symlink")
    if must_exist and kind == "file" and not candidate.is_file():
        raise ValueError("input must be a regular file")
    if must_exist and kind == "directory" and not candidate.is_dir():
        raise ValueError("workspace must be a directory")
    return candidate


def dispatch(request):
    if set(request) - {"schema_version", "operation", "workspace", "payload"}:
        raise ValueError("unknown request field")
    if request.get("schema_version") != 1 or not isinstance(request.get("payload", {}), dict):
        raise ValueError("invalid request schema")
    operation = request.get("operation")
    payload = request.get("payload", {})
    if operation == "handshake":
        return {"schema_version": 1, "adapter": "gr4", "evidence": "reference_verified"}
    if operation == "allocate_version":
        from gr4_editor.versions import allocate_version
        return {"version": allocate_version(payload.get("source"), payload.get("ledger", ()),
                                             payload.get("requested"))}
    workspace = confined(request.get("workspace"), request.get("workspace"),
                         must_exist=True, kind="directory")
    from gr4_editor.service import Editor
    editor = Editor(workspace / "data")
    if operation in {"inspect", "import"}:
        source = confined(workspace, payload.get("input_path"), must_exist=True)
        if operation == "inspect":
            from gr4_editor.firmware import inspect_firmware, load_image
            return inspect_firmware(load_image(source))
        return editor.import_firmware(source.read_bytes(), payload.get("filename", source.name))
    if operation == "status":
        return editor.status()
    if operation == "settings":
        return editor.settings()
    if operation == "project":
        return editor.project(payload.get("project_id"))
    if operation in {"save", "project_save"}:
        return editor.save(payload.get("project_id"), payload.get("title"), payload.get("crops"),
                           payload.get("shutdown"), build_options=payload.get("build_options"),
                           filters=payload.get("filters"))
    if operation == "project_import":
        return editor.import_project(payload.get("project"))
    if operation == "project_export":
        return editor.project(payload.get("project_id"))
    if operation == "filter_add":
        return editor.add_filter(payload.get("project_id"), payload.get("template_id"), payload.get("name"))
    if operation == "filter_remove":
        return editor.remove_filter(payload.get("project_id"), payload.get("filter_id"))
    if operation in {"xmp_import", "icon_import", "shutdown_image", "shutdown_import"}:
        source = confined(workspace, payload.get("input_path") or payload.get("image_path"), must_exist=True)
        data = source.read_bytes()
        if operation == "xmp_import":
            return editor.import_xmp(payload.get("project_id"), payload.get("filter_id"), data,
                                     payload.get("filename", source.name), payload.get("render_engine", "offline"))
        if operation == "icon_import":
            return editor.import_icon(payload.get("project_id"), payload.get("filter_id"), data)
        return editor.import_shutdown_image(payload.get("project_id"), payload.get("target_id"), data,
                                            payload.get("filename", source.name), payload.get("fit", "contain"),
                                            payload.get("item_id"), payload.get("item_name"))
    if operation == "calibration_state":
        return editor.calibration_state(payload.get("project_id"), payload.get("filter_id"))
    if operation == "calibration_register":
        return editor.register_calibration(payload.get("samples"), payload.get("heldout"))
    if operation == "calibration_run":
        return editor.run_calibration(payload.get("project_id"), payload.get("filter_id"),
                                      payload.get("render_engine"))
    if operation == "calibration_output":
        target = editor.calibration_output(payload.get("job_id"), payload.get("filename", ""))
        return {"path": str(confined(workspace, target, must_exist=True)), "filename": target.name}
    if operation == "crop_preview":
        return editor.crop_preview(payload.get("project_id"), payload.get("ratio"))
    if operation in {"shutdown_add", "shutdown_item"}:
        return editor.add_shutdown_item(payload.get("project_id"), payload.get("name"),
                                        payload.get("source_id"), payload.get("asset_id"))
    if operation == "shutdown_export":
        data = editor.export_shutdown(payload.get("project_id"))
        target = workspace / "data" / "exports" / (payload.get("project_id") + "-shutdown.zip")
        target = confined(workspace, target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return {"path": str(target), "filename": "shutdown-preparation.zip", "bytes": len(data)}
    if operation == "build":
        result = editor.build(payload.get("project_id"), payload.get("version"), payload.get("allow_older"))
        result["evidence"] = "reference_verified"
        return result
    if operation == "build_download":
        record = editor.store.build(payload.get("build_id"))
        if not record:
            raise ValueError("build not found")
        kind = payload.get("kind", "firmware")
        if kind not in {"firmware", "manifest"}:
            raise ValueError("invalid build artifact kind")
        target = Path(record["firmware_path" if kind == "firmware" else "manifest_path"])
        return {"path": str(confined(workspace, target, must_exist=True)), "filename": target.name}
    if operation == "history":
        return editor.firmware_history(payload.get("project_id"))
    if operation == "history_open":
        return editor.open_history_firmware(payload.get("sha256"))
    if operation in {"rollback", "history_rollback"}:
        result = editor.rollback_history_firmware(payload.get("sha256"), payload.get("project_id"),
                                                  payload.get("version"), payload.get("allow_older", True))
        result["evidence"] = "reference_verified"
        return result
    if operation == "history_download":
        target = editor.history_firmware_path(payload.get("sha256"))
        return {"path": str(confined(workspace, target, must_exist=True)), "filename": target.name}
    if operation == "toolchain_save":
        from gr4_editor.toolchain import save_config
        return save_config(editor.store.root, payload.get("clang"), payload.get("lld") or None)
    raise ValueError("unknown operation")


def main():
    raw = sys.stdin.buffer.read(MAX_REQUEST + 1)
    if len(raw) > MAX_REQUEST:
        raise ValueError("request exceeds 192 MiB")
    request = json.loads(raw)
    result = dispatch(request)
    sys.stdout.write(json.dumps({"ok": True, "result": result}, ensure_ascii=False,
                                separators=(",", ":")) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        sys.stdout.write(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False,
                                    separators=(",", ":")) + "\n")
