from dataclasses import dataclass
from typing import List, Optional
import json
from pathlib import Path


@dataclass
class Product:
    id: str
    name: str
    description: str
    price: float
    currency: str = "EUR"
    image_url: str = ""
    category: str = "General"
    stock: int = 100
    supplier: str = "AliExpress"
    weight: Optional[float] = None
    dimensions: Optional[str] = None


class ProductCatalog:
    def __init__(self):
        self.products: List[Product] = []
        self._load_products()

    def _load_products(self):
        """Load products from JSON file or create default products"""
        products_file = Path("data/products.json")

        if products_file.exists():
            try:
                with open(products_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for p in data:
                        self.products.append(Product(**p))
            except Exception as e:
                print(f"Error loading products: {e}")
                self._create_default_products()
        else:
            self._create_default_products()

    def _create_default_products(self):
        """Create default sample products for dropshipping"""
        self.products = [
            Product(
                id="ai_robot_kit",
                name="AI Robot Building Kit",
                description="Complete kit to build your own AI-powered robot. Includes sensors, motors, and programming board.",
                price=49.99,
                currency="EUR",
                image_url="https://images.unsplash.com/photo-1485827404703-89b55fcc595e?w=400",
                category="Electronics",
                stock=50,
                supplier="AliExpress",
                weight=2.5,
                dimensions="30x20x10 cm"
            ),
            Product(
                id="quantum_optimizer",
                name="Quantum Code Optimizer",
                description="Advanced AI tool that optimizes your code for maximum performance and quantum efficiency.",
                price=29.99,
                currency="EUR",
                image_url="https://images.unsplash.com/photo-1555949963-aa79dcee981c?w=400",
                category="Software",
                stock=100,
                supplier="Digital Download",
                weight=0.0
            ),
            Product(
                id="neural_network_board",
                name="Neural Network Development Board",
                description="Powerful board for developing neural networks and machine learning applications.",
                price=79.99,
                currency="EUR",
                image_url="https://images.unsplash.com/photo-1517077304055-6e89abbf09b0?w=400",
                category="Electronics",
                stock=25,
                supplier="AliExpress",
                weight=1.2,
                dimensions="15x10x5 cm"
            ),
            Product(
                id="automation_suite",
                name="Business Automation Suite",
                description="Complete automation package for small businesses. Includes workflow optimization and AI assistants.",
                price=99.99,
                currency="EUR",
                image_url="https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=400",
                category="Software",
                stock=75,
                supplier="Digital Download",
                weight=0.0
            ),
            Product(
                id="robot_sensor_pack",
                name="Advanced Robot Sensor Pack",
                description="Collection of high-quality sensors for robotics projects including ultrasonic, infrared, and temperature sensors.",
                price=34.99,
                currency="EUR",
                image_url="https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?w=400",
                category="Electronics",
                stock=40,
                supplier="AliExpress",
                weight=0.8,
                dimensions="20x15x8 cm"
            ),
            Product(
                id="ai_training_course",
                name="AI Training Course Bundle",
                description="Comprehensive online course covering machine learning, deep learning, and AI implementation.",
                price=19.99,
                currency="EUR",
                image_url="https://images.unsplash.com/photo-1522202176988-66273c2fd55f?w=400",
                category="Education",
                stock=200,
                supplier="Digital Download",
                weight=0.0
            )
        ]
        self._save_products()

    def _save_products(self):
        """Save products to JSON file"""
        products_file = Path("data/products.json")
        products_file.parent.mkdir(parents=True, exist_ok=True)

        data = [vars(p) for p in self.products]
        with open(products_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_all_products(self) -> List[Product]:
        """Get all products"""
        return self.products

    def get_product_by_id(self, product_id: str) -> Optional[Product]:
        """Get product by ID"""
        for product in self.products:
            if product.id == product_id:
                return product
        return None

    def get_products_by_category(self, category: str) -> List[Product]:
        """Get products by category"""
        return [p for p in self.products if p.category.lower() == category.lower()]

    def get_categories(self) -> List[str]:
        """Get unique categories"""
        return list(set(p.category for p in self.products))

    def add_product(self, product: Product):
        """Add a new product"""
        self.products.append(product)
        self._save_products()

    def update_product(self, product_id: str, **updates):
        """Update product details"""
        product = self.get_product_by_id(product_id)
        if product:
            for key, value in updates.items():
                if hasattr(product, key):
                    setattr(product, key, value)
            self._save_products()

    def remove_product(self, product_id: str):
        """Remove a product"""
        self.products = [p for p in self.products if p.id != product_id]
        self._save_products()


# Global catalog instance
catalog = ProductCatalog()