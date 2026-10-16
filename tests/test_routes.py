######################################################################
# Copyright 2016, 2023 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
######################################################################
"""
Product API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
  codecov --token=$CODECOV_TOKEN

  While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_service.py:TestProductService
"""
import os
import logging
from decimal import Decimal
from unittest import TestCase
from service import app
from service.common import status
from service.models import db, init_db, Product
from tests.factories import ProductFactory

# Disable all but critical errors during normal test run
# uncomment for debugging failing tests
# logging.disable(logging.CRITICAL)

# DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///../db/test.db')
DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)
BASE_URL = "/products"


######################################################################
#  T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductRoutes(TestCase):
    """Product Service tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        # Set up the test database
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client()
        db.session.query(Product).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        db.session.remove()

    ############################################################
    # Utility function to bulk create products
    ############################################################
    def _create_products(self, count: int = 1) -> list:
        """Factory method to create products in bulk"""
        products = []
        for _ in range(count):
            test_product = ProductFactory()
            response = self.client.post(BASE_URL, json=test_product.serialize())
            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, "Could not create test product"
            )
            new_product = response.get_json()
            test_product.id = new_product["id"]
            products.append(test_product)
        return products

    ############################################################
    #  T E S T   C A S E S
    ############################################################
    def test_index(self):
        """It should return the index page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b"Product Catalog Administration", response.data)

    def test_health(self):
        """It should be healthy"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data['message'], 'OK')

    # ----------------------------------------------------------
    # TEST CREATE
    # ----------------------------------------------------------
    def test_create_product(self):
        """It should Create a new Product"""
        test_product = ProductFactory()
        logging.debug("Test Product: %s", test_product.serialize())
        response = self.client.post(BASE_URL, json=test_product.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["description"], test_product.description)
        self.assertEqual(Decimal(new_product["price"]), test_product.price)
        self.assertEqual(new_product["available"], test_product.available)
        self.assertEqual(new_product["category"], test_product.category.name)

        #
        # Uncomment this code once READ is implemented
        #

        # # Check that the location header was correct
        # response = self.client.get(location)
        # self.assertEqual(response.status_code, status.HTTP_200_OK)
        # new_product = response.get_json()
        # self.assertEqual(new_product["name"], test_product.name)
        # self.assertEqual(new_product["description"], test_product.description)
        # self.assertEqual(Decimal(new_product["price"]), test_product.price)
        # self.assertEqual(new_product["available"], test_product.available)
        # self.assertEqual(new_product["category"], test_product.category.name)

    def test_create_product_with_no_name(self):
        """It should not Create a Product without a name"""
        product = self._create_products()[0]
        new_product = product.serialize()
        del new_product["name"]
        logging.debug("Product no name: %s", new_product)
        response = self.client.post(BASE_URL, json=new_product)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_product_no_content_type(self):
        """It should not Create a Product with no Content-Type"""
        response = self.client.post(BASE_URL, data="bad data")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_create_product_wrong_content_type(self):
        """It should not Create a Product with wrong Content-Type"""
        response = self.client.post(BASE_URL, data={}, content_type="plain/text")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_get_product(self):
        """Read an existing product."""
        product = self._create_products()[0]
        response = self.client.get(f"{BASE_URL}/{product.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json(), product.serialize())

    def test_get_product_not_found(self):
        """Return 404 for an unknown product."""
        response = self.client.get(f"{BASE_URL}/0")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_product(self):
        """Update an existing product."""
        product = self._create_products()[0]
        payload = product.serialize()
        payload["description"] = "Updated description"
        response = self.client.put(f"{BASE_URL}/{product.id}", json=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json()["description"], "Updated description")

    def test_update_product_not_found(self):
        """Return 404 when updating an unknown product."""
        response = self.client.put(f"{BASE_URL}/0", json=ProductFactory().serialize())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_product_wrong_content_type(self):
        """Reject an update with an invalid content type."""
        product = self._create_products()[0]
        response = self.client.put(f"{BASE_URL}/{product.id}", data="bad data")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_delete_product(self):
        """Delete a product and verify its removal."""
        products = self._create_products(5)
        original_count = self.get_product_count()
        response = self.client.delete(f"{BASE_URL}/{products[0].id}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(response.data)
        response = self.client.get(f"{BASE_URL}/{products[0].id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.get_product_count(), original_count - 1)

    def test_delete_product_not_found(self):
        """Deleting a missing product remains idempotent."""
        response = self.client.delete(f"{BASE_URL}/0")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_list_all_products(self):
        """List all products."""
        self.assertEqual(self.get_product_count(), 0)
        self._create_products(5)
        self.assertEqual(self.get_product_count(), 5)

    def test_list_by_name(self):
        """Filter products by exact name."""
        products = self._create_products(5)
        name = products[0].name
        response = self.client.get(BASE_URL, query_string={"name": name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        matches = response.get_json()
        self.assertEqual(len(matches), sum(p.name == name for p in products))
        self.assertTrue(all(p["name"] == name for p in matches))

    def test_list_by_category(self):
        """Filter products by category."""
        products = self._create_products(10)
        category = products[0].category.name
        response = self.client.get(BASE_URL, query_string={"category": category})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        matches = response.get_json()
        self.assertEqual(len(matches), sum(p.category.name == category for p in products))
        self.assertTrue(all(p["category"] == category for p in matches))

    def test_list_by_availability(self):
        """Filter products by availability."""
        products = self._create_products(10)
        available = products[0].available
        response = self.client.get(BASE_URL, query_string={"available": str(available)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        matches = response.get_json()
        self.assertEqual(len(matches), sum(p.available == available for p in products))
        self.assertTrue(all(p["available"] == available for p in matches))

    def test_list_invalid_category(self):
        """Return 400 for unknown category."""
        response = self.client.get(BASE_URL, query_string={"category": "NONEXISTENT"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_invalid_availability(self):
        """Return 400 for invalid availability filter."""
        response = self.client.get(BASE_URL, query_string={"available": "possibly"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    ######################################################################
    # Utility functions
    ######################################################################

    def get_product_count(self):
        """save the current number of products"""
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        # logging.debug("data = %s", data)
        return len(data)
