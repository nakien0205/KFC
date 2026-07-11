import shutil
import subprocess
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TestCustomerFrontend(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node.js is required to exercise the browser script offline.")
    def test_offer_price_invalidation_and_menu_image_fallback(self):
        harness = textwrap.dedent(
            """
            const fs = require('fs');
            const vm = require('vm');
            class Element {
              constructor() { this.innerHTML = ''; this._textContent = ''; this.dataset = {}; this.attrs = {}; this.disabled = false; this.style = {}; }
              set textContent(value) { this._textContent = String(value); this.innerHTML = String(value); }
              get textContent() { return this._textContent; }
              setAttribute(name, value) { this.attrs[name] = String(value); }
              addEventListener() {}
              querySelectorAll() { return []; }
            }
            const elements = {};
            global.window = { __CUSTOMER_APP_TEST__: true };
            global.document = {
              createElement: () => new Element(),
              getElementById: (id) => elements[id] || (elements[id] = new Element())
            };
            vm.runInThisContext(fs.readFileSync('static/customer/app.js', 'utf8'));
            const hooks = window.__customerAppTestHooks;
            const pepsi = { name: 'Pepsi', category: 'Drinks', price: 19000, image: 'pepsi.png' };
            const fries = { name: 'French Fries', category: 'Sides', price: 30000 };
            const brokenImage = {
              dataset: { itemName: 'Pepsi' },
              addEventListener: (event, listener) => { if (event === 'error') brokenImage.onError = listener; },
              replaceWith: (replacement) => { brokenImage.replacement = replacement; }
            };
            elements['menu-grid'].querySelectorAll = (selector) => selector === 'img.menu-image' ? [brokenImage] : [];
            hooks.setMenu([pepsi, fries]);
            hooks.renderMenu();
            let state = hooks.getState();
            if (!state.menuMarkup.includes('/static/images/pepsi.png') || !state.menuMarkup.includes('alt="Photo of Pepsi"')) throw new Error('image missing');
            if (!state.menuMarkup.includes('aria-label="No image available for French Fries"')) throw new Error('fallback missing');
            brokenImage.onError();
            if (!brokenImage.replacement || brokenImage.replacement.attrs['aria-label'] !== 'No image available for Pepsi') throw new Error('broken image fallback missing');
            hooks.applyPersonalOffer({ offer_id: 'personal-pepsi', target_item: 'Pepsi', sale_price: 10000 });
            state = hooks.getState();
            if (state.total !== '10.000 VND' || !state.cartMarkup.includes('10.000 VND')) throw new Error('offer price not displayed');
            hooks.queueRecommendations();
            if (!hooks.getState().recommendationStatus.includes('reserved')) throw new Error('offer refresh was not held');
            hooks.add(pepsi);
            state = hooks.getState();
            if (state.activeOfferId !== null || state.total !== '38.000 VND') throw new Error('invalid offer was retained');
            if (hooks.checkoutPayload().offer_id !== null) throw new Error('invalid offer would be submitted');
            hooks.resetCart();
            hooks.applyPersonalOffer({ offer_id: 'personal-pepsi', target_item: 'Pepsi', sale_price: 10000 });
            hooks.remove('Pepsi');
            state = hooks.getState();
            if (state.activeOfferId !== null || hooks.checkoutPayload().offer_id !== null) throw new Error('removed offer was retained');
            """
        )
        result = subprocess.run(
            ["node", "-e", harness], cwd=ROOT, text=True, capture_output=True, check=False
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()
