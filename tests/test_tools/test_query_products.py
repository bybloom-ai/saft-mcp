"""Tests for the saft_query_products tool."""

from pathlib import Path

import pytest

from saft_mcp.parser.full_parser import parse_saft_file
from saft_mcp.state import SessionState
from saft_mcp.tools.query_products import query_products

REAL_DATA_DIR = Path(__file__).parent.parent.parent / "Saft Josefinas 2025"
REAL_FULL_YEAR = REAL_DATA_DIR / "5108036012025_Completo.xml"


@pytest.fixture(scope="module")
def loaded_session():
    if not REAL_FULL_YEAR.exists():
        pytest.skip("Real SAF-T files not available")
    session = SessionState()
    session.loaded_file = parse_saft_file(str(REAL_FULL_YEAR))
    return session


class TestQueryProducts:
    def test_no_file_loaded(self):
        session = SessionState()
        result = query_products(session)
        assert "error" in result

    def test_unfiltered_query(self, loaded_session):
        result = query_products(loaded_session)
        assert "total_count" in result
        assert "returned_count" in result
        assert "products" in result
        assert result["total_count"] == 429

    def test_product_structure(self, loaded_session):
        result = query_products(loaded_session, limit=1)
        prod = result["products"][0]
        assert "product_code" in prod
        assert "product_description" in prod
        assert "product_type" in prod
        assert "product_group" in prod
        assert "product_number_code" in prod
        assert "times_sold" in prod
        assert "total_quantity" in prod
        assert "total_revenue" in prod

    def test_filter_by_description(self, loaded_session):
        # Get a product description fragment to search for
        all_prods = query_products(loaded_session, limit=1)
        desc_fragment = all_prods["products"][0]["product_description"][:5]
        result = query_products(loaded_session, description=desc_fragment)
        assert result["total_count"] > 0
        for prod in result["products"]:
            assert desc_fragment.lower() in prod["product_description"].lower()

    def test_filter_by_code(self, loaded_session):
        all_prods = query_products(loaded_session, limit=1)
        code_fragment = all_prods["products"][0]["product_code"][:3]
        result = query_products(loaded_session, code=code_fragment)
        assert result["total_count"] > 0
        for prod in result["products"]:
            assert code_fragment in prod["product_code"]

    def test_filter_by_product_type(self, loaded_session):
        result = query_products(loaded_session, product_type="P", limit=500)
        for prod in result["products"]:
            assert prod["product_type"] == "P"

    def test_sales_stats(self, loaded_session):
        result = query_products(loaded_session, limit=500)
        # At least some products should have been sold
        sold_products = [p for p in result["products"] if p["times_sold"] > 0]
        assert len(sold_products) > 0
        for prod in sold_products:
            assert prod["times_sold"] > 0

    def test_pagination(self, loaded_session):
        page1 = query_products(loaded_session, limit=5, offset=0)
        assert page1["returned_count"] <= 5
        if page1["has_more"]:
            page2 = query_products(loaded_session, limit=5, offset=5)
            ids1 = {p["product_code"] for p in page1["products"]}
            ids2 = {p["product_code"] for p in page2["products"]}
            assert ids1.isdisjoint(ids2)

    def test_limit_capped_at_max(self, loaded_session):
        result = query_products(loaded_session, limit=9999)
        assert result["returned_count"] <= 500

    def test_combined_filters(self, loaded_session):
        # Get a product type that exists
        all_prods = query_products(loaded_session, limit=1)
        ptype = all_prods["products"][0]["product_type"]
        desc_fragment = all_prods["products"][0]["product_description"][:3]
        result = query_products(
            loaded_session, product_type=ptype, description=desc_fragment
        )
        for prod in result["products"]:
            assert prod["product_type"] == ptype
            assert desc_fragment.lower() in prod["product_description"].lower()
