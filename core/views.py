from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from .email_service import EmailManager
from .models import (
    ProjectDetail,
    NavigationLink,
    FooterSection,
    Slider,
    About,
    FeatureCard,
    Game,
    Platform,
    Event,
    Footer,
    SectionHeading,
)


def base_site_context():
    # Common site-wide context used across core pages
    project_detail = ProjectDetail.objects.filter(is_active=True).first()
    footer = Footer.objects.filter(is_active=True).first()
    footer_sections = FooterSection.objects.filter(is_active=True).prefetch_related('links')
    
    return {
        'project_detail': project_detail,
        'footer': footer,
        'footer_sections': footer_sections,
    }


def get_section_headings():
    # Helper function to get all section headings as a dictionary keyed by slug
    headings = {}
    for heading in SectionHeading.objects.filter(is_active=True).select_related('section'):
        headings[heading.section.slug] = heading
    return headings


def index(request):
    base_context = base_site_context()
    
    # Get section headings
    headings = get_section_headings()
    
    navigation_links = NavigationLink.objects.filter(is_active=True)
    sliders = Slider.objects.filter(is_active=True).order_by('order')
    about = About.objects.filter(is_active=True).first()
    features = FeatureCard.objects.filter(is_active=True).order_by('order')
    
    # Use slugs for easy reference
    game_heading = headings.get('games')
    games = Game.objects.filter(is_active=True)
    
    platform_heading = headings.get('platforms')
    platforms = Platform.objects.filter(is_active=True).order_by('order')
    
    event_heading = headings.get('events')
    events = Event.objects.filter(is_active=True)
    
    context = {
        **base_context,
        'navigation_links': navigation_links,
        'sliders': sliders,
        'about': about,
        'features': features,
        'game_heading': game_heading,
        'games': games,
        'platform_heading': platform_heading,
        'platforms': platforms,
        'event_heading': event_heading,
        'events': events,
        'all_headings': headings,  # Pass all headings
    }
    
    return render(request, 'core/index.html', context)


def cookie_policy(request):
    context = base_site_context()
    return render(request, 'core/legal/cookie_policy.html', context)


def terms_conditions(request):
    context = base_site_context()
    return render(request, 'core/legal/terms.html', context)


def privacy_policy(request):
    context = base_site_context()
    return render(request, 'core/legal/privacy_policy.html', context)


def faqs(request):
    context = base_site_context()
    return render(request, 'core/support/faqs.html', context)


def contact_us(request):
    context = base_site_context()
    return render(request, 'core/support/contact.html', context)


def help_center(request):
    context = base_site_context()
    return render(request, 'core/support/help_center.html', context)


def help_creating_account(request):
    context = base_site_context()
    return render(request, 'core/support/guides/creating_account.html', context)


def help_platform_navigation(request):
    context = base_site_context()
    return render(request, 'core/support/guides/platform_navigation.html', context)


def help_first_tournament(request):
    context = base_site_context()
    return render(request, 'core/support/guides/first_tournament.html', context)


@require_POST
@csrf_exempt
def contact_submit(request):
    # Handle contact form submission and email support.
    
    name = f"{request.POST.get('first_name', '').strip()} {request.POST.get('last_name', '').strip()}".strip()
    email = request.POST.get('email', '').strip()
    subject_type = request.POST.get('subject', '').strip() or 'other'
    message_body = request.POST.get('message', '').strip()
    urgent = request.POST.get('urgent') == 'on'
    
    if not name or not email or not message_body:
        return JsonResponse({
            'success': False,
            'message': 'Please fill in all required fields.'
        }, status=400)
    
    # Build email subject and body
    email_subject = f"[Contact] {subject_type.title()} - {name}"
    if urgent:
        email_subject = "[URGENT] " + email_subject
    
    full_message = (
        f"From: {name} <{email}>\n"
        f"Subject type: {subject_type}\n"
        f"Urgent: {'Yes' if urgent else 'No'}\n\n"
        f"Message:\n{message_body}"
    )
    
    sent = EmailManager.send_support_contact(email_subject, full_message, from_email=email)
    
    if sent:
        return JsonResponse({
            'success': True,
            'message': 'Thank you! Your message has been sent successfully.'
        })
    return JsonResponse({
        'success': False,
        'message': 'Sorry, there was an error sending your message. Please try again later.'
    }, status=500)