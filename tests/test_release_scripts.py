from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_qualification_limits_s3_parallelism_and_cleans_warmup_first():
    script = (ROOT / "tools/qualify-release.sh").read_text()
    cleanup = 'cleanup_managed_build "${warmup_label//-/_}"'
    first_group = "first_managed_group=("
    assert script.index(cleanup) < script.index(first_group)
    group = script.split(first_group, 1)[1].split(")", 1)[0]
    assert group.count("-s3.yaml") == 1
    assert group.count("-esp32.yaml") == 1
    assert 'run_managed_group first-managed "${first_managed_group[@]}"' in script
    assert 'run_managed_group second-managed "${second_managed_group[@]}"' in script
    assert 'df -Pk "${managed_build_root}"' in script
