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

"""
Test cases for Product Model

Test cases can be run with:
    nosetests
    coverage report -m

While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_models.py:TestProductModel

"""
import os
import logging
import unittest
from decimal import Decimal
from service.models import Product, Category, DataValidationError, db
from service import app
from tests.factories import ProductFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)


######################################################################
#  P R O D U C T   M O D E L   T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductModel(unittest.TestCase):
    """Test Cases for Product Model"""

    @classmethod
    def setUpClass(cls):
        """This runs once before the entire test suite"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        Product.init_db(app)

    @classmethod
    def tearDownClass(cls):
        """This runs once after the entire test suite"""
        db.session.close()

    def setUp(self):
        """This runs before each test"""
        db.session.query(Product).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        """This runs after each test"""
        db.session.remove()

    ######################################################################
    #  T E S T   C A S E S
    ######################################################################

    def test_create_a_product(self):
        """It should Create a product and assert that it exists"""
        product = Product(name="Fedora", description="A red hat", price=12.50, available=True, category=Category.CLOTHS)
        self.assertEqual(str(product), "<Product Fedora id=[None]>")
        self.assertTrue(product is not None)
        self.assertEqual(product.id, None)
        self.assertEqual(product.name, "Fedora")
        self.assertEqual(product.description, "A red hat")
        self.assertEqual(product.available, True)
        self.assertEqual(product.price, 12.50)
        self.assertEqual(product.category, Category.CLOTHS)

    def test_add_a_product(self):
        """It should Create a product and add it to the database"""
        products = Product.all()
        self.assertEqual(products, [])
        product = ProductFactory()
        product.id = None
        product.create()
        # Assert that it was assigned an id and shows up in the database
        self.assertIsNotNone(product.id)
        products = Product.all()
        self.assertEqual(len(products), 1)
        # Check that it matches the original product
        new_product = products[0]
        self.assertEqual(new_product.name, product.name)
        self.assertEqual(new_product.description, product.description)
        self.assertEqual(Decimal(new_product.price), product.price)
        self.assertEqual(new_product.available, product.available)
        self.assertEqual(new_product.category, product.category)

    def test_read_a_product(self):
        """Read an existing product by its ID."""
        product = ProductFactory()
        product.id = None
        product.create()
        self.assertIsNotNone(product.id)
        found = Product.find(product.id)
        self.assertIsNotNone(found)
        self.assertEqual(found.id, product.id)
        self.assertEqual(found.name, product.name)
        self.assertEqual(found.description, product.description)
        self.assertEqual(Decimal(found.price), product.price)
        self.assertEqual(found.available, product.available)
        self.assertEqual(found.category, product.category)

    def test_update_a_product(self):
        """Update a saved product."""
        product = ProductFactory()
        product.create()
        product_id = product.id
        product.description = "testing"
        product.update()
        self.assertEqual(product.id, product_id)
        products = Product.all()
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].id, product_id)
        self.assertEqual(products[0].description, "testing")

    def test_delete_a_product(self):
        """Remove a product from the database."""
        product = ProductFactory()
        product.create()
        self.assertEqual(len(Product.all()), 1)
        product.delete()
        self.assertEqual(len(Product.all()), 0)
        self.assertIsNone(Product.find(product.id))

    def test_list_all_products(self):
        """List every product in the database."""
        self.assertEqual(Product.all(), [])
        products = ProductFactory.create_batch(5)
        for product in products:
            product.create()
        self.assertEqual(len(Product.all()), 5)

    def test_find_product_by_name(self):
        """Filter products by name."""
        products = ProductFactory.create_batch(5)
        for product in products:
            product.create()
        target = products[0].name
        matches = list(Product.find_by_name(target))
        self.assertEqual(len(matches), sum(p.name == target for p in products))
        self.assertTrue(all(p.name == target for p in matches))

    def test_find_product_by_category(self):
        """Filter products by category."""
        products = ProductFactory.create_batch(10)
        for product in products:
            product.create()
        target = products[0].category
        matches = list(Product.find_by_category(target))
        self.assertEqual(len(matches), sum(p.category == target for p in products))
        self.assertTrue(all(p.category == target for p in matches))

    def test_find_product_by_availability(self):
        """Filter products by availability."""
        products = ProductFactory.create_batch(10)
        for product in products:
            product.create()
        target = products[0].available
        matches = list(Product.find_by_availability(target))
        self.assertEqual(len(matches), sum(p.available == target for p in products))
        self.assertTrue(all(p.available == target for p in matches))

    def test_update_without_id_rejected(self):
        """An unsaved product cannot be updated."""
        product = ProductFactory()
        product.id = None
        with self.assertRaises(DataValidationError):
            product.update()

    def test_deserialize_bad_availability(self):
        """Reject a string in place of the availability boolean."""
        data = ProductFactory().serialize()
        data["available"] = "yes"
        with self.assertRaises(DataValidationError):
            Product().deserialize(data)

    def test_deserialize_invalid_category(self):
        """Reject an invalid category identifier."""
        data = ProductFactory().serialize()
        data["category"] = "INVALID"
        with self.assertRaises(DataValidationError):
            Product().deserialize(data)

    def test_deserialize_missing_name(self):
        """Reject incomplete product JSON."""
        data = ProductFactory().serialize()
        del data["name"]
        with self.assertRaises(DataValidationError):
            Product().deserialize(data)

    def test_deserialize_non_mapping(self):
        """Reject a non-dictionary body."""
        with self.assertRaises(DataValidationError):
            Product().deserialize(None)

    def test_find_product_by_price(self):
        """Find products with numeric and string price filters."""
        product = ProductFactory(price=Decimal("12.50"))
        product.create()
        self.assertEqual(len(list(Product.find_by_price(Decimal("12.50")))), 1)
        self.assertEqual(len(list(Product.find_by_price("12.50"))), 1)
