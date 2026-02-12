"""Tests for data analysis tools."""

from __future__ import annotations

import json
from pathlib import Path

from jarvis.tools.data import read_csv, csv_stats, parse_json, transform_json


def test_read_csv(tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("name,age,score\nAlice,30,85\nBob,25,92\nCharlie,35,78\n")
    result = read_csv(str(csv_file))
    assert "Alice" in result
    assert "Bob" in result
    assert "name" in result
    assert "age" in result


def test_read_csv_not_found():
    result = read_csv("/nonexistent.csv")
    assert "not found" in result.lower()


def test_csv_stats(tmp_path):
    csv_file = tmp_path / "stats.csv"
    csv_file.write_text("name,value\nA,10\nB,20\nC,30\nD,40\n")
    result = csv_stats(str(csv_file), "value")
    assert "Count: 4" in result
    assert "Min: 10" in result
    assert "Max: 40" in result
    assert "Mean: 25" in result


def test_csv_stats_all_columns(tmp_path):
    csv_file = tmp_path / "multi.csv"
    csv_file.write_text("x,y,label\n1,10,a\n2,20,b\n3,30,c\n")
    result = csv_stats(str(csv_file))
    assert "Column: x" in result
    assert "Column: y" in result


def test_parse_json(tmp_path):
    json_file = tmp_path / "test.json"
    json_file.write_text(json.dumps({"name": "Jarvis", "version": 2}))
    result = parse_json(str(json_file))
    assert "Jarvis" in result
    assert "version" in result


def test_parse_json_with_query(tmp_path):
    json_file = tmp_path / "nested.json"
    data = {"users": [{"name": "Alice"}, {"name": "Bob"}]}
    json_file.write_text(json.dumps(data))
    result = parse_json(str(json_file), "users[0].name")
    assert "Alice" in result


def test_parse_json_not_found():
    result = parse_json("/nonexistent.json")
    assert "not found" in result.lower()


def test_transform_json(tmp_path):
    input_file = tmp_path / "input.json"
    output_file = tmp_path / "output.json"
    data = [
        {"name": "Alice", "age": 30, "city": "NYC"},
        {"name": "Bob", "age": 25, "city": "LA"},
        {"name": "Charlie", "age": 35, "city": "NYC"},
    ]
    input_file.write_text(json.dumps(data))

    result = transform_json(
        str(input_file),
        str(output_file),
        "filter:city=NYC|select:name,age",
    )
    assert "2 records" in result
    assert output_file.exists()

    output_data = json.loads(output_file.read_text())
    assert len(output_data) == 2
    assert output_data[0]["name"] == "Alice"
    assert "city" not in output_data[0]


def test_transform_json_sort(tmp_path):
    input_file = tmp_path / "sort_input.json"
    output_file = tmp_path / "sort_output.json"
    data = [{"name": "Charlie"}, {"name": "Alice"}, {"name": "Bob"}]
    input_file.write_text(json.dumps(data))

    transform_json(str(input_file), str(output_file), "sort:name")
    output_data = json.loads(output_file.read_text())
    assert output_data[0]["name"] == "Alice"
    assert output_data[2]["name"] == "Charlie"
