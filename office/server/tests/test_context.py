"""context.py 테스트.

[HOONI] 아래 test_tree_excludes_noise 는 예시다. 나머지를 직접 채워라:
  - assemble_brief() — subprocess.run 을 monkeypatch 해서 고정 git log → 결과에 포함
  - brief.md 가 없어도 예외 없이 커밋/트리 섹션만 반환 (monkeypatch 로 _BRIEF 경로를 없는 파일로)
막히면 물어봐라.
"""
import context


def test_tree_excludes_noise(tmp_path, monkeypatch):
    # 가짜 레포 트리를 만든다
    (tmp_path / "backend-ai").mkdir()
    (tmp_path / "office").mkdir()
    (tmp_path / ".git").mkdir()
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "README.md").write_text("x")
    monkeypatch.setattr(context.settings.__class__, "repo_root_path",
                        property(lambda self: tmp_path), raising=False)

    tree = context._tree(tmp_path)
    assert "backend-ai/" in tree
    assert "README.md" in tree
    assert "office" not in tree
    assert "node_modules" not in tree
    assert ".git" not in tree
