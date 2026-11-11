from policy_assistant.policy_chunks import policy_chunks


def test_numbered_conditions_keep_distinct_search_centers_and_adjacent_context():
    content = "Bản mẫu\n\n1. Hàng lỗi được đề nghị kiểm tra.\n2. Đổi ý cần còn nguyên hộp.\n3. Phí bảo hành chưa quy định."
    chunks = policy_chunks(content)
    assert any(c["section_text"] == "1. Hàng lỗi được đề nghị kiểm tra." for c in chunks)
    middle = next(c for c in chunks if c["section_text"].startswith("2."))
    assert "1. Hàng lỗi" in middle["text"] and "3. Phí bảo hành" in middle["text"]


def test_long_neighbor_cannot_displace_the_matched_clause():
    chunks = policy_chunks("A" * 1400 + "\n\n2. Điều kiện quan trọng cần được giữ nguyên.")
    for chunk in chunks:
        assert chunk["section_text"] in chunk["text"]
        assert len(chunk["text"]) <= 1400
    assert any("Điều kiện quan trọng" in chunk["text"] for chunk in chunks)


def test_many_tiny_paragraphs_have_bounded_index_cost_and_keep_content():
    content = "\n\n".join(str(n) for n in range(2000))
    chunks = policy_chunks(content)
    assert len(chunks) <= 64
    assert chunks[0]["section_text"] == content[:1400]
    assert str(1999) in chunks[-1]["text"]
