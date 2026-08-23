import json
from pathlib import Path

from app.services.client_assets import find_downloaded_asset, list_downloaded_assets


def test_client_asset_catalog_returns_only_verified_downloads(tmp_path: Path) -> None:
    client_id = "11111111-1111-4111-8111-111111111111"
    submission_id = "22222222-2222-4222-8222-222222222222"
    submission_directory = tmp_path / "clients" / client_id / "submissions" / submission_id
    image_path = submission_directory / "images" / "good_outfits" / "01.jpg"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"synthetic-image")
    (submission_directory / "manifest.json").write_text(
        json.dumps(
            {
                "submission_id": submission_id,
                "assets": [
                    {
                        "field_key": "good_outfit",
                        "ordinal": 1,
                        "drive_folder": "good_outfits",
                        "status": "downloaded",
                        "filename": "01.jpg",
                        "content_type": "image/jpeg",
                        "local_relative_path": (
                            f"clients/{client_id}/submissions/{submission_id}/"
                            "images/good_outfits/01.jpg"
                        ),
                    },
                    {
                        "field_key": "missing_image",
                        "ordinal": 1,
                        "drive_folder": "bad_outfits",
                        "status": "download_failed",
                        "local_relative_path": "clients/missing.jpg",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    assets = list_downloaded_assets(tmp_path, client_id)

    assert len(assets) == 1
    assert assets[0].folder_label == "Good Outfits"
    assert assets[0].path == image_path.resolve()
    assert find_downloaded_asset(
        tmp_path,
        client_id=client_id,
        submission_id=submission_id,
        field_key="good_outfit",
        ordinal=1,
    ) == assets[0]


def test_client_asset_catalog_rejects_paths_outside_root(tmp_path: Path) -> None:
    client_id = "33333333-3333-4333-8333-333333333333"
    submission_id = "44444444-4444-4444-8444-444444444444"
    submission_directory = tmp_path / "clients" / client_id / "submissions" / submission_id
    submission_directory.mkdir(parents=True)
    outside_path = tmp_path.parent / "not-an-asset.jpg"
    outside_path.write_bytes(b"synthetic-image")
    (submission_directory / "manifest.json").write_text(
        json.dumps(
            {
                "submission_id": submission_id,
                "assets": [
                    {
                        "field_key": "escape",
                        "ordinal": 1,
                        "drive_folder": "questionnaire",
                        "status": "downloaded",
                        "local_relative_path": "../../not-an-asset.jpg",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    assert list_downloaded_assets(tmp_path, client_id) == []
