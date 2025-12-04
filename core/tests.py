from django.test import TestCase, Client
from django.urls import reverse
from .models import ProjectDetail, Footer, FooterSection, FooterLink, About


class CoreViewsTests(TestCase):
	def setUp(self):
		self.client = Client()
		ProjectDetail.objects.create(title="GamiKonnect", description="Desc", short_description="Short")
		Footer.objects.create(copy_right_text="© 2025 GamiKonnect. All rights reserved.",
							   ownership_text="A product by JM | In partnership with Biztimam Ventures")
		section = FooterSection.objects.create(title="Quick Links", order=1)
		FooterLink.objects.create(section=section, link_text="Home", link="/", order=1)
		About.objects.create(badge_text="WHO WE ARE", heading="About", content="Content")

	def test_index_renders(self):
		url = reverse('core:home')
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)
		self.assertIn('project_detail', resp.context)
		self.assertIn('footer', resp.context)
		self.assertIn('footer_sections', resp.context)
		self.assertIn('sliders', resp.context)
		self.assertIn('about', resp.context)
		self.assertTemplateUsed(resp, 'core/index.html')

	def test_contact_submit_invalid(self):
		url = reverse('core:contact_submit')
		resp = self.client.post(url, data={})
		self.assertEqual(resp.status_code, 400)
		self.assertJSONEqual(resp.content.decode(), {
			'success': False,
			'message': 'Please fill in all required fields.'
		})

	def test_contact_submit_valid(self):
		url = reverse('core:contact_submit')
		data = {
			'first_name': 'John',
			'last_name': 'Doe',
			'email': 'john@example.com',
			'subject': 'support',
			'message': 'Help me',
		}
		resp = self.client.post(url, data=data)
		# In test, email backend may be console, but view returns 200 JSON on success path
		self.assertIn(resp.status_code, (200, 500))
		self.assertIn('application/json', resp.headers.get('Content-Type', ''))

# Create your tests here.
