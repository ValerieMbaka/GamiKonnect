from django import forms
from django.utils import timezone
from .models import Competition, CompetitionRegistration, CompetitionResult


# Competition Creation Form
class CompetitionCreateForm(forms.ModelForm):
    class Meta:
        model = Competition
        fields = [
            'name', 'description', 'game', 'platform', 'shop',
            'scheduled_time', 'competition_end_time',
            'entry_fee', 'max_participants', 'team_size',
            'gender_rules', 'is_pwa_only', 'age_restricted', 'rules',
        ]
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Describe the competition...',
            }),
            'scheduled_time': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
            }),
            'competition_end_time': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
            }),
            'rules': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'List the competition rules...',
            }),
            'entry_fee': forms.NumberInput(attrs={
                'min': '0',
                'step': '0.01',
                'placeholder': '0.00',
            }),
            'max_participants': forms.NumberInput(attrs={
                'min': '2',
                'placeholder': 'e.g. 16',
            }),
            'team_size': forms.NumberInput(attrs={
                'min': '1',
                'placeholder': '1',
            }),
            'gender_rules': forms.Select(),
            'is_pwa_only': forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        # Accept an optional shop_owner kwarg to filter the shop dropdown
        # to only the shops owned by the creating shop owner.
        self.shop_owner = kwargs.pop('shop_owner', None)
        super().__init__(*args, **kwargs)

        if self.shop_owner:
            self.fields['shop'].queryset = self.shop_owner.shops.filter(is_approved=True)

        # Filter platforms to only those supported by the selected game.
        self.fields['platform'].queryset = self.fields['platform'].queryset.order_by('name')
        self.fields['game'].queryset = self.fields['game'].queryset.filter(
            is_active=True
        ).order_by('name')

    def clean(self):
        cleaned_data = super().clean()
        scheduled_time = cleaned_data.get('scheduled_time')
        competition_end_time = cleaned_data.get('competition_end_time')

        # Competition must be scheduled in the future
        if scheduled_time and scheduled_time <= timezone.now():
            self.add_error('scheduled_time', 'The competition must be scheduled for a future date and time.')

        # End time must be after start time
        if scheduled_time and competition_end_time:
            if competition_end_time <= scheduled_time:
                self.add_error(
                    'competition_end_time',
                    'Competition end time must be after the scheduled start time.'
                )

        # Platform must be supported by the selected game
        game = cleaned_data.get('game')
        platform = cleaned_data.get('platform')
        if game and platform:
            if not game.supported_platforms.filter(pk=platform.pk).exists():
                self.add_error('platform', 'The selected platform is not supported by this game.')

        # Platform must be available at the selected shop
        shop = cleaned_data.get('shop')
        if shop and platform:
            if not shop.consoles.filter(console_type=platform).exists():
                self.add_error('platform', 'The selected platform is not available at this shop.')

        # Game must be available at the selected shop
        if shop and game:
            if not shop.games_available.filter(pk=game.pk).exists():
                self.add_error('game', 'The selected game is not available at this shop.')

        return cleaned_data


# Competition Edit Form (used by shop owner after rejection)
class CompetitionEditForm(CompetitionCreateForm):
    """
    Identical to CompetitionCreateForm but used when a shop owner
    edits a rejected competition before resubmission.
    The shop field is locked to prevent moving a competition to a different shop.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Lock the shop field — cannot change shop after initial submission
        self.fields['shop'].disabled = True


# Competition Approval Form
class CompetitionApprovalForm(forms.ModelForm):
    class Meta:
        model = Competition
        fields = [
            # Entry fee — admin can adjust
            'entry_fee',

            # Rules — admin can review and edit combined rules
            'rules',

            # Registration window — set by admin
            'registration_opens_at',
            'registration_closes_at',

            # Prize
            'prize_type',

            # Points prize
            'points_1st', 'points_2nd', 'points_3rd',
            'points_4_to_10', 'points_beyond_10',

            # Money prize
            'prize_money_total',
            'prize_money_1st_pct', 'prize_money_2nd_pct', 'prize_money_3rd_pct',

            # Gift prize
            'prize_gift_description',
        ]
        widgets = {
            'registration_opens_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'registration_closes_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'entry_fee': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
            'rules': forms.Textarea(attrs={
                'rows': 6,
                'placeholder': 'Review and edit all rules here. Default age/ID requirements are pre-filled...',
            }),
            'prize_gift_description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Describe the gift prize and how it is distributed across the top 3...',
            }),
            'prize_money_total': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
            'prize_money_1st_pct': forms.NumberInput(attrs={'min': '0', 'max': '100'}),
            'prize_money_2nd_pct': forms.NumberInput(attrs={'min': '0', 'max': '100'}),
            'prize_money_3rd_pct': forms.NumberInput(attrs={'min': '0', 'max': '100'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        prize_type = cleaned_data.get('prize_type')
        scheduled_time = self.instance.scheduled_time
        opens_at = cleaned_data.get('registration_opens_at')
        closes_at = cleaned_data.get('registration_closes_at')

        # Registration window validations
        if not opens_at:
            self.add_error('registration_opens_at', 'Registration open time is required.')
        if not closes_at:
            self.add_error('registration_closes_at', 'Registration close time is required.')

        if opens_at and closes_at:
            if opens_at >= closes_at:
                self.add_error(
                    'registration_closes_at',
                    'Registration must close after it opens.'
                )
            if opens_at <= timezone.now():
                self.add_error(
                    'registration_opens_at',
                    'Registration open time must be in the future.'
                )

        if closes_at and scheduled_time:
            if closes_at >= scheduled_time:
                self.add_error(
                    'registration_closes_at',
                    'Registration must close before the competition starts.'
                )

        # Prize type validations
        if not prize_type:
            self.add_error('prize_type', 'Please select a prize type.')

        if prize_type == 'points':
            if not cleaned_data.get('points_1st'):
                self.add_error('points_1st', 'Points for 1st place are required.')
            if not cleaned_data.get('points_2nd'):
                self.add_error('points_2nd', 'Points for 2nd place are required.')
            if not cleaned_data.get('points_3rd'):
                self.add_error('points_3rd', 'Points for 3rd place are required.')

        if prize_type == 'money':
            if not cleaned_data.get('prize_money_total'):
                self.add_error('prize_money_total', 'Total prize money is required.')
            pct_1st = cleaned_data.get('prize_money_1st_pct') or 0
            pct_2nd = cleaned_data.get('prize_money_2nd_pct') or 0
            pct_3rd = cleaned_data.get('prize_money_3rd_pct') or 0
            if pct_1st + pct_2nd + pct_3rd > 100:
                self.add_error(
                    'prize_money_3rd_pct',
                    'Total prize money percentages cannot exceed 100%.'
                )

        if prize_type == 'gift':
            if not cleaned_data.get('prize_gift_description'):
                self.add_error('prize_gift_description', 'Please describe the gift prize.')

        return cleaned_data


# Competition Rejection Form
class CompetitionRejectionForm(forms.ModelForm):
    class Meta:
        model = Competition
        fields = ['rejection_reason']
        widgets = {
            'rejection_reason': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Provide a clear reason for rejection so the shop owner can make the necessary changes...',
            }),
        }

    def clean_rejection_reason(self):
        reason = self.cleaned_data.get('rejection_reason', '').strip()
        if not reason:
            raise forms.ValidationError('A rejection reason is required.')
        return reason


# Competition Registration Form
class CompetitionRegistrationForm(forms.ModelForm):
    # PWA checkbox — user confirms their PWA status for this registration
    is_pwa = forms.BooleanField(
        required=False,
        label="I am PWA (Person With Albinism or other specified status)",
        help_text="Check this box if applicable to this competition's PWA requirements."
    )
    
    class Meta:
        model = CompetitionRegistration
        fields = []
        # No model fields in the form — competition and gamer are set in the view.
        # The form's purpose is to collect the PWA flag and trigger model-level validation.

    def __init__(self, *args, **kwargs):
        # Accept competition and gamer from the view for validation context
        self.competition = kwargs.pop('competition', None)
        self.gamer = kwargs.pop('gamer', None)
        super().__init__(*args, **kwargs)
        # Assign to instance BEFORE validation so model clean() can access them
        if self.instance:
            self.instance.competition = self.competition
            self.instance.gamer = self.gamer

    def clean(self):
        cleaned_data = super().clean()

        if not self.competition or not self.gamer:
            raise forms.ValidationError('Invalid registration request.')

        # Competition must be open for registration
        if self.competition.status != 'registration_open':
            raise forms.ValidationError('Registration for this competition is not currently open.')

        # Registration must not be full
        if self.competition.is_registration_full():
            raise forms.ValidationError('This competition has reached its maximum number of participants.')

        # Gamer must not already be registered
        if CompetitionRegistration.objects.filter(
            competition=self.competition,
            gamer=self.gamer,
            is_cancelled=False
        ).exists():
            raise forms.ValidationError('You are already registered for this competition.')
        
        # PWA requirement check
        is_pwa_checked = cleaned_data.get('is_pwa', False)
        if self.competition.is_pwa_only and not is_pwa_checked:
            raise forms.ValidationError('This competition is only for PWA. Please confirm your PWA status.')
        
        return cleaned_data
    
    def save(self, commit=True):
        # Save the PWA status to the gamer's profile
        is_pwa = self.cleaned_data.get('is_pwa', False)
        if self.gamer:
            self.gamer.is_pwa = is_pwa
            self.gamer.save(update_fields=['is_pwa'])
        
        # Save the registration
        return super().save(commit=commit)

        # Age restriction check
        if self.competition.age_restricted:
            dob = self.gamer.date_of_birth
            if dob:
                today = timezone.now().date()
                age = today.year - dob.year - (
                    (today.month, today.day) < (dob.month, dob.day)
                )
                if age < 18:
                    raise forms.ValidationError(
                        'You must be 18 years or older to register for this competition.'
                    )
            else:
                raise forms.ValidationError(
                    'Your date of birth is not set. Please update your profile before registering.'
                )

        # Shop owner restriction — cannot register for competitions at their own shop
        from accounts.models import ShopOwner
        try:
            shop_owner = ShopOwner.objects.get(uid=self.gamer.uid)
            if shop_owner.shops.filter(pk=self.competition.shop.pk).exists():
                raise forms.ValidationError(
                    'You cannot register for a competition held at your own shop.'
                )
        except ShopOwner.DoesNotExist:
            pass  # Pure gamer — no restriction

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.competition = self.competition
        instance.gamer = self.gamer
        if commit:
            instance.save()
        return instance


# Check-in Submission Form
class GamerCheckInForm(forms.ModelForm):
    class Meta:
        model = CompetitionRegistration
        fields = ['checked_in']
        widgets = {
            'checked_in': forms.CheckboxInput(),
        }


# Results Submission Form
class CompetitionResultForm(forms.ModelForm):
    class Meta:
        model = CompetitionResult
        fields = ['gamer', 'rank', 'is_no_show']
        widgets = {
            'rank': forms.NumberInput(attrs={'min': '1', 'placeholder': 'e.g. 1'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        rank = cleaned_data.get('rank')
        is_no_show = cleaned_data.get('is_no_show')

        # A no-show gamer should not have a rank
        if is_no_show and rank:
            self.add_error('rank', 'A no-show gamer should not have a rank assigned.')

        # A non-no-show gamer must have a rank
        if not is_no_show and not rank:
            self.add_error('rank', 'Please assign a rank or mark this gamer as a no-show.')

        return cleaned_data


# Admin Competition Creation Form (Includes approval fields)
class CompetitionAdminCreateForm(forms.ModelForm):
    class Meta:
        model = Competition
        fields = [
            # Core details
            'name', 'description', 'game', 'platform', 'shop',
            'scheduled_time', 'competition_end_time',
            'entry_fee', 'max_participants',
            'age_restricted', 'rules',
            
            # Registration windows
            'registration_opens_at', 'registration_closes_at',
            
            # Prize
            'prize_type',
            'points_1st', 'points_2nd', 'points_3rd',
            'points_4_to_10', 'points_beyond_10',
            'prize_money_total',
            'prize_money_1st_pct', 'prize_money_2nd_pct', 'prize_money_3rd_pct',
            'prize_gift_description',
        ]
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Describe the competition...',
            }),
            'scheduled_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'competition_end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'registration_opens_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'registration_closes_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'rules': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'List the competition rules...',
            }),
            'entry_fee': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
            'max_participants': forms.NumberInput(attrs={'min': '1'}),
            'prize_gift_description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Describe the gift prize and how it is distributed...',
            }),
            'prize_money_total': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
            'prize_money_1st_pct': forms.NumberInput(attrs={'min': '0', 'max': '100'}),
            'prize_money_2nd_pct': forms.NumberInput(attrs={'min': '0', 'max': '100'}),
            'prize_money_3rd_pct': forms.NumberInput(attrs={'min': '0', 'max': '100'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter games and shops based on active/approved status
        from games.models import Game
        from shops.models import Shop
        self.fields['game'].queryset = Game.objects.filter(is_active=True)
        self.fields['shop'].queryset = Shop.objects.filter(is_approved=True)

    def clean(self):
        cleaned_data = super().clean()
        scheduled_time = cleaned_data.get('scheduled_time')
        opens_at = cleaned_data.get('registration_opens_at')
        closes_at = cleaned_data.get('registration_closes_at')
        prize_type = cleaned_data.get('prize_type')
        competition_end_time = cleaned_data.get('competition_end_time')
        
        now = timezone.now()

        # Scheduled time validation
        if scheduled_time and scheduled_time <= now:
            self.add_error('scheduled_time', 'Competition must be scheduled for a future time.')

        # Registration window validations
        if not opens_at:
            self.add_error('registration_opens_at', 'Registration open time is required.')
        if not closes_at:
            self.add_error('registration_closes_at', 'Registration close time is required.')

        if opens_at and closes_at:
            if opens_at >= closes_at:
                self.add_error('registration_closes_at', 'Registration must close after it opens.')
            if opens_at <= now:
                self.add_error('registration_opens_at', 'Registration open time must be in the future.')

        if closes_at and scheduled_time:
            if closes_at >= scheduled_time:
                self.add_error('registration_closes_at', 'Registration must close before the competition starts.')

        # End time validation (if provided)
        if competition_end_time and scheduled_time:
            if competition_end_time <= scheduled_time:
                self.add_error('competition_end_time', 'Competition end time must be after the start time.')

        # Prize type validations
        if not prize_type:
            self.add_error('prize_type', 'Please select a prize type.')

        if prize_type == 'points':
            if not cleaned_data.get('points_1st'):
                self.add_error('points_1st', 'Points for 1st place are required.')
            if not cleaned_data.get('points_2nd'):
                self.add_error('points_2nd', 'Points for 2nd place are required.')
            if not cleaned_data.get('points_3rd'):
                self.add_error('points_3rd', 'Points for 3rd place are required.')

        if prize_type == 'money':
            if not cleaned_data.get('prize_money_total'):
                self.add_error('prize_money_total', 'Total prize money is required.')
            pct_1st = cleaned_data.get('prize_money_1st_pct') or 0
            pct_2nd = cleaned_data.get('prize_money_2nd_pct') or 0
            pct_3rd = cleaned_data.get('prize_money_3rd_pct') or 0
            if pct_1st + pct_2nd + pct_3rd > 100:
                self.add_error('prize_money_3rd_pct', 'Total prize money percentages cannot exceed 100%.')

        if prize_type == 'gift':
            if not cleaned_data.get('prize_gift_description'):
                self.add_error('prize_gift_description', 'Please describe the gift prize.')

        return cleaned_data