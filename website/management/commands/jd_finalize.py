import os

from django.core.management.base import BaseCommand, CommandError
from mezzanine.conf.models import Setting
from mezzanine.blog.models import BlogCategory
from mezzanine.pages.models import Page, Link
from mezzanine.utils.sites import current_site_id
from mezzanine.conf import settings
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from janeus.models import JaneusRole
from optparse import make_option
from website.jdpages.models import Sidebar, SidebarTwitterWidget, SidebarBlogCategoryWidget, PageHeaderImageWidget, BlogCategoryPage, HorizontalPosition, ColumnElement, ColumnElementWidget, EventColumnElement
from hemres.models import NewsletterTemplate, MailingList
from filebrowser_safe import settings as fb_settings
from shutil import copy

def save_setting(name, value, domain):
    s = Setting()
    site = Site.objects.get(domain = domain)
    s.name = name
    s.value = value
    s.site = site
    s.save()

def save_group(name):
    g = Group()
    g.name = name
    g.save()

def save_group_permissions(groupname, permissionCodenames):
    g = Group.objects.get(name = groupname)
    for permCodename in permissionCodenames:
        p = Permission.objects.get(codename = permCodename)
        g.permissions.add(p)
    g.save()

def save_janeus_role(role, groupnames, sites):
    j = JaneusRole()
    j.role = role
    j.save()
    for groupname in groupnames:
        g = Group.objects.get(name = groupname)
        j.groups.add(g)
    for site in sites:
        s = Site.objects.get(domain = site)
        j.sites.add(s)
    j.save()

def activate_twitter_widget():
    s = Sidebar.objects.all()[0]
    widget, created = SidebarTwitterWidget.objects.get_or_create(sidebar = s)
    widget.active = True
    widget.save()

def force_create_uploads_directory():
    uploadDir = os.path.join(settings.MEDIA_ROOT,
                             fb_settings.DIRECTORY,
                             'site-{0}'.format(current_site_id()))
    os.makedirs(uploadDir, exist_ok = True)
    os.chmod(uploadDir, 0o755)
    os.makedirs(os.path.join(uploadDir, 'headers'), exist_ok = True)
    os.chmod(os.path.join(uploadDir, 'headers'), 0o755)
    os.makedirs(os.path.join(uploadDir, 'blogs-pages'), exist_ok = True)
    os.chmod(os.path.join(uploadDir, 'blogs-pages'), 0o755)
    os.makedirs(os.path.join(uploadDir, 'documents'), exist_ok = True)
    os.chmod(os.path.join(uploadDir, 'documents'), 0o755)

def set_header_image(slug, image_url):
    pages = Page.objects.filter(slug = slug)
    if len(pages) == 0:
        print ("Page not found with slug {0}".format(slug))
    elif len(pages) > 1:
        print ("Several pages found with slug {0}".format(slug))
    else:
        p = pages[0]
        w = PageHeaderImageWidget(name = p.site.name+"-"+slug, page = p, image = image_url)
        w.save()

def set_headers():
    prefix = Site.objects.get(id = current_site_id()).domain.split('.')[0]
    headerDir = os.path.join(settings.PROJECT_ROOT, '..', '..', 'new-headers')
    dirList = os.listdir(headerDir)
    uploadDirRel = os.path.join(settings.MEDIA_URL,
                             fb_settings.DIRECTORY,
                             'site-{0}'.format(current_site_id()))
    uploadDirAbs = os.path.join(settings.PROJECT_ROOT, uploadDirRel.lstrip('/'))
    for headerSubDir in dirList:
        if headerSubDir.startswith(prefix + '-'):
            slug = headerSubDir.split('-', 1)[1]
            if slug == '*':
                slug = '/'
            for image in os.listdir(os.path.join(headerDir, headerSubDir)):
                copy(os.path.join(headerDir, headerSubDir, image),
                     os.path.join(uploadDirAbs, 'headers'))
                os.chmod(os.path.join(uploadDirAbs, 'headers', image), 0o644)
                print("Setting header {0} for {1} - {2}".format(image, prefix, slug))
                set_header_image(slug, os.path.join(uploadDirRel, 'headers', image))

def create_column_element_widget(slug, hp, title, columnElement, numItems):
    """
    Function to create column elements. Should only be called through create_*_column_element_widget functions.
    """
    if hp == 'l':
        hp = HorizontalPosition.LEFT
    else:
        hp = HorizontalPosition.RIGHT
    p = Page.objects.get(slug = slug)
    cew = ColumnElementWidget(column_element = columnElement, page = p)
    cew.title = title
    cew.horizontal_position = hp
    cew.max_items = numItems
    cew.save()
    print("Imported column element {0} on {1} ({2}).".format(title, slug, current_site_id()))

def create_events_column_element_widget(slug, calendars, hp, title, numItems = 5):
    """
    Add a ColumnElementWidget to a Page with slug 'slug' for Events calendar calendars (one of
    EventColumnElement.EVENT_CHOICES), horizontal position hp (one of 'l' or 'r') with title 'title'
    and number of items numItems (default 5).

    (str, str, str, str, str, int) -> None
    """
    ece = EventColumnElement.objects.get(type = calendars)
    ce = ColumnElement.objects.get(object_id = ece.id, content_type = ContentType.objects.get_for_model(ece))
    create_column_element_widget(slug, hp, title, ce, numItems)

def create_blog_category_column_element_widget(slug, category, hp, title = None, st = "", numItems = 3):
    """
    Add a ColumnElementWidget to a Page with slug 'slug' for BlogCategory with name category at
    horizontal position hp (one of 'l' or 'r') with title 'title', subtype st (default "")
    and number of items numItems (default 3).

    (str, str, HorizontalPosition, str, str, int) -> None
    """
    cat = BlogCategory.objects.get(title = category)
    if title is None:
        title = category
    ce = ColumnElement.objects.get(object_id = cat.id, content_type = ContentType.objects.get_for_model(cat), subtype = st)
    create_column_element_widget(slug, hp, title, ce, numItems)

def create_column_element_widgets(domain):
    if (domain == 'website.jongedemocraten.nl'):
        create_blog_category_column_element_widget('/', "Politieke opinie", 'l', "Politiek")
        create_blog_category_column_element_widget('/', "Mededelingen", 'r', 'Mededelingen')
        create_blog_category_column_element_widget('media', "Persberichten", 'l', numItems = 5)
        create_blog_category_column_element_widget('media', "JD in de Media", 'r', 'JD in de media', numItems = 5)
    if (domain == 'amsterdam.jongedemocraten.nl'):
        create_events_column_element_widget('/', 'SI', 'l', "Geplande activiteiten Amsterdam")
        create_events_column_element_widget('/', 'MA', 'l', "Geplande activiteiten landelijk")
        create_blog_category_column_element_widget('/', "Nieuws", 'r', "Laatste nieuws Amsterdam", st = 'CP', numItems = 5)
        create_blog_category_column_element_widget('/', "Opinie", 'r', "De Druppel: Recente artikelen", st = 'CP', numItems = 5)
        create_blog_category_column_element_widget('de-druppel', "Opinie", 'l', "Meest recente artikelen", numItems = 5)
        create_blog_category_column_element_widget('de-druppel', "Activiteiten", 'r', st = 'CP')
        create_blog_category_column_element_widget('de-druppel', "Reportages", 'r', st = 'CP')
        create_blog_category_column_element_widget('de-druppel', "Interviews", 'r', st = 'CP')
        create_blog_category_column_element_widget('de-druppel', "Opinie", 'r', st = 'CP')
        create_blog_category_column_element_widget('de-druppel', "Column", 'r', st = 'CP')
    if (domain == 'rotterdam.jongedemocraten.nl'):
        create_events_column_element_widget('/', 'SM', 'l', "Geplande activiteiten Rotterdam")
        create_blog_category_column_element_widget('/', "Nieuws", 'r', "Laatste nieuws Rotterdam", st = 'CP', numItems = 5)
        create_blog_category_column_element_widget('oh-ja-joh', "Oh ja joh?", 'l', "Meest recente artikelen", numItems = 5)
    if (domain == 'arnhemnijmegen.jongedemocraten.nl'):
        pass
    if (domain == 'brabant.jongedemocraten.nl'):
        create_events_column_element_widget('/', 'SI', 'l', "Geplande activiteiten Brabant")
        create_blog_category_column_element_widget('/', "Nieuws", 'r', "Laatste nieuws Brabant", st = 'CP', numItems = 5)
    if (domain == 'groningen.jongedemocraten.nl'):
        create_events_column_element_widget('/', 'SI', 'l', "Geplande activiteiten Groningen")
        create_events_column_element_widget('/', 'MA', 'l', "Geplande activiteiten landelijk")
        create_blog_category_column_element_widget('/', "Nieuws", 'r', "Laatste nieuws Groningen", st = 'CP', numItems = 5)
        create_blog_category_column_element_widget('/', "Weblog", 'r', "Weblogs", st = 'CP', numItems = 5)
    if (domain == 'leidenhaaglanden.jongedemocraten.nl'):
        create_events_column_element_widget('/', 'SI', 'l', "Activiteiten Leiden-Haaglanden")
        create_events_column_element_widget('/', 'MA', 'l', "Geplande activiteiten landelijk")
        create_blog_category_column_element_widget('/', "Nieuws", 'r', "Laatste nieuws", st = 'CP', numItems = 5)
        create_blog_category_column_element_widget('/', "Weblog", 'r', "Weblogs", st = 'CP', numItems = 5)
    if (domain == 'twente.jongedemocraten.nl'):
        create_events_column_element_widget('/', 'SI', 'l', "Geplande activiteiten Twente")
        create_blog_category_column_element_widget('/', "Nieuws", 'r', 'Laatste nieuws Twente', st = 'CP', numItems = 5)
    if (domain == 'friesland.jongedemocraten.nl'):
        pass
    if (domain == 'fryslan.jongedemocraten.nl'):
        pass
    if (domain == 'internationaal.jongedemocraten.nl'):
        pass
    if (domain == 'limburg.jongedemocraten.nl'):
        create_events_column_element_widget('/', 'SI', 'l', "Geplande activiteiten Limburg")
        create_events_column_element_widget('/', 'MA', 'l', "Geplande activiteiten landelijk")
        create_blog_category_column_element_widget('/', "Nieuws", 'r', "Laatste nieuws Limburg", st = 'CP', numItems = 5)
    if (domain == 'utrecht.jongedemocraten.nl'):
        create_events_column_element_widget('/', 'SI', 'l', "Geplande activiteiten Utrecht")
        create_events_column_element_widget('/', 'MA', 'l', "Geplande activiteiten landelijk")
        create_blog_category_column_element_widget('/', "Nieuws", 'r', "Laatste nieuws", st = 'CP', numItems = 5)
        create_blog_category_column_element_widget('/', "Weblog", 'r', "Weblogs", st = 'CP', numItems = 5)

def create_page_for_each_blog_category():
    categories = BlogCategory.objects.all()
    for c in categories:
        try:
            p = Page.objects.get(slug = c.slug)
            return
        except Page.DoesNotExist:
            pass
        b, created = BlogCategoryPage.objects.get_or_create(slug = c.slug, blog_category = c)
        if created:
            b.title = c.title
            b.save()

def set_sidebar_blog(category, title = None):
    if title is None:
        title = category
    sb = Sidebar.objects.get()
    cat = BlogCategory.objects.get(title = category)
    w = SidebarBlogCategoryWidget(title = title, sidebar = sb, blog_category = cat)
    w.save()

def set_sidebar_blogs_for_domain(domain):
    if (domain == 'website.jongedemocraten.nl'):
        set_sidebar_blog("Weblog", "JD Blog")
    if (domain == 'amsterdam.jongedemocraten.nl'):
        set_sidebar_blog("Nieuws")
        set_sidebar_blog("Opinie", "De Druppel")
    if (domain == 'arnhemnijmegen.jongedemocraten.nl'):
        set_sidebar_blog("Nieuws")
        set_sidebar_blog("Weblog")
    if (domain == 'brabant.jongedemocraten.nl'):
        set_sidebar_blog("Nieuws")
        set_sidebar_blog("Weblog")
    if (domain == 'groningen.jongedemocraten.nl'):
        set_sidebar_blog("Nieuws")
        set_sidebar_blog("Weblog")
    if (domain == 'leidenhaaglanden.jongedemocraten.nl'):
        set_sidebar_blog("Nieuws")
        set_sidebar_blog("Weblog")
    if (domain == 'rotterdam.jongedemocraten.nl'):
        set_sidebar_blog("Nieuws")
        set_sidebar_blog("Oh ja joh?")
    if (domain == 'twente.jongedemocraten.nl'):
        set_sidebar_blog("Nieuws")
    if (domain == 'friesland.jongedemocraten.nl'):
        set_sidebar_blog("Nieuws")
    if (domain == 'internationaal.jongedemocraten.nl'):
        set_sidebar_blog("Weblog", "Weblog Internationaal")
    if (domain == 'limburg.jongedemocraten.nl'):
        set_sidebar_blog("Nieuws")
    if (domain == 'utrecht.jongedemocraten.nl'):
        set_sidebar_blog("Nieuws")
        set_sidebar_blog("Weblog")

def create_mailinglist(label, name):
    m = MailingList()
    m.label = label
    m.name = name
    m.save()

def create_newsletter_template(title, template):
    n = NewsletterTemplate()
    n.title = title
    n.template = template
    n.save()

def create_mailinglists_and_templates():
    pass

def create_link(title, link):
    l = Link()
    l.title = title
    l.slug = link
    l.save()

def twitter_query_for_domain(domain):
    if (domain == 'website.jongedemocraten.nl'):
        return 'jongedemocraten'
    if (domain == 'amsterdam.jongedemocraten.nl'):
        return 'JDAmsterdam'
    if (domain == 'arnhemnijmegen.jongedemocraten.nl'):
        return 'JDArnhmNijmgn'
    if (domain == 'brabant.jongedemocraten.nl'):
        return 'JD_Brabant'
    if (domain == 'groningen.jongedemocraten.nl'):
        return 'JD_Groningen'
    if (domain == 'leidenhaaglanden.jongedemocraten.nl'):
        return 'JDLeiDenHaageo'
    if (domain == 'rotterdam.jongedemocraten.nl'):
        return 'JD_Rotterdam'
    if (domain == 'twente.jongedemocraten.nl'):
        return 'JDTwente'
    if (domain == 'friesland.jongedemocraten.nl'):
        return 'jongedemocraten'
    if (domain == 'internationaal.jongedemocraten.nl'):
        return 'jongedemocraten'
    if (domain == 'limburg.jongedemocraten.nl'):
        return 'JDLimburg'
    if (domain == 'utrecht.jongedemocraten.nl'):
        return 'jongedemocraten'

    return 'jongedemocraten' # Default

class Command(BaseCommand):
    help = 'Set permissions, settings and other values.'
    option_list = BaseCommand.option_list + (
        make_option('--twitterconsumerkey',
                    dest='twitterconsumerkey',
                    default='',
                    help='TWITTER_CONSUMER_KEY'),
        make_option('--twitterconsumersecret',
                    dest='twitterconsumersecret',
                    default='',
                    help='TWITTER_CONSUMER_SECRET'),
        make_option('--twitteraccesstokenkey',
                    dest='twitteraccesstokenkey',
                    default='',
                    help='TWITTER_ACCESS_TOKEN_KEY'),
        make_option('--twitteraccesstokensecret',
                    dest='twitteraccesstokensecret',
                    default='',
                    help='TWITTER_ACCESS_TOKEN_SECRET')
    )


    def handle(self, *args, **options):
        sites = Site.objects.all()
        for site in sites:
            os.environ["MEZZANINE_SITE_ID"] = str(site.id)
            name = site.name
            site_id = site.id
            domain = site.domain
            print("Processing settings for {0}".format(domain))
            if (domain == 'website.jongedemocraten.nl'):
                save_setting('SITE_TAGLINE', '', domain)
                save_setting('SITE_TITLE', 'Jonge Democraten', domain)
            else:
                save_setting('SITE_TAGLINE', name, domain)
                save_setting('SITE_TITLE', 'Jonge Democraten {0}'.format(name), domain)

            save_setting('TWITTER_CONSUMER_KEY',
                options['twitterconsumerkey'], domain)
            save_setting('TWITTER_CONSUMER_SECRET',
                options['twitterconsumersecret'], domain)
            save_setting('TWITTER_ACCESS_TOKEN_KEY',
                options['twitteraccesstokenkey'], domain)
            save_setting('TWITTER_ACCESS_TOKEN_SECRET',
                options['twitteraccesstokensecret'], domain)
            save_setting('TWITTER_DEFAULT_NUM_TWEETS', '3', domain)
            save_setting('TWITTER_DEFAULT_QUERY',
                twitter_query_for_domain(domain), domain)
            save_setting('TWITTER_DEFAULT_QUERY_TYPE', 'search', domain)
            save_setting('ADMIN_MENU_COLLAPSED', 'False', domain)
            save_setting('BLOG_POST_PER_PAGE', '5', domain)
            save_setting('MAX_PAGING_LINKS', '10', domain)
            save_setting('RICHTEXT_FILTER_LEVEL', '1', domain)
            save_setting('PIWIK_SITE_ID', site_id, domain)
            save_setting('SEARCH_PER_PAGE', '10', domain)
            if (domain == 'website.jongedemocraten.nl'):
                save_setting('SIDEBAR_AGENDA_SITES', '3', domain)
            else:
                save_setting('SIDEBAR_AGENDA_SITES', '2', domain)

            create_page_for_each_blog_category()
            activate_twitter_widget()
            force_create_uploads_directory()
            set_headers()
            create_column_element_widgets(domain)
            set_sidebar_blogs_for_domain(domain)

        create_mailinglists_and_templates()
        
        save_group('Administrators')
        save_group('Master Content Managers')
        save_group('Content Managers')
        save_group('Publishers')
        
        save_group_permissions('Administrators', [
            "add_assignedkeyword",
            "add_blogcategory",
            "add_blogcategorypage",
            "add_blogpost",
            "add_captchastore",
            "add_columnelement",
            "add_columnelementwidget",
            "add_comment",
            "add_commentflag",
            "add_contenttype",
            "add_document",
            "add_documentlisting",
            "add_emailsubscriber",
            "add_emailsubscriberaccesstoken",
            "add_event",
            "add_eventcategory",
            "add_eventcolumnelement",
            "add_field",
            "add_fieldentry",
            "add_form",
            "add_formentry",
            "add_gallery",
            "add_galleryimage",
            "add_group",
            "add_homepage",
            "add_janeusrole",
            "add_janeussubscriber",
            "add_janeussubscriberaccesstoken",
            "add_janeususer",
            "add_keyword",
            "add_link",
            "add_logentry",
            "add_mailinglist",
            "add_newsletter",
            "add_newslettertemplate",
            "add_newslettertolist",
            "add_newslettertosubscriber",
            "add_occurrence",
            "add_page",
            "add_pageheaderimagewidget",
            "add_permission",
            "add_query",
            "add_rating",
            "add_redirect",
            "add_richtextpage",
            "add_session",
            "add_setting",
            "add_sidebar",
            "add_sidebarbannerwidget",
            "add_sidebarblogcategorywidget",
            "add_sidebartabswidget",
            "add_sidebartwitterwidget",
            "add_site",
            "add_sitepermission",
            "add_socialmediabutton",
            "add_subscriber",
            "add_threadedcomment",
            "add_tweet",
            "add_user",
            "can_moderate",
            "change_assignedkeyword",
            "change_blogcategory",
            "change_blogcategorypage",
            "change_blogpost",
            "change_captchastore",
            "change_columnelement",
            "change_columnelementwidget",
            "change_comment",
            "change_commentflag",
            "change_contenttype",
            "change_document",
            "change_documentlisting",
            "change_emailsubscriber",
            "change_emailsubscriberaccesstoken",
            "change_event",
            "change_eventcategory",
            "change_eventcolumnelement",
            "change_field",
            "change_fieldentry",
            "change_form",
            "change_formentry",
            "change_gallery",
            "change_galleryimage",
            "change_group",
            "change_homepage",
            "change_janeusrole",
            "change_janeussubscriber",
            "change_janeussubscriberaccesstoken",
            "change_janeususer",
            "change_keyword",
            "change_link",
            "change_logentry",
            "change_mailinglist",
            "change_newsletter",
            "change_newslettertemplate",
            "change_newslettertolist",
            "change_newslettertosubscriber",
            "change_occurrence",
            "change_page",
            "change_pageheaderimagewidget",
            "change_permission",
            "change_query",
            "change_rating",
            "change_redirect",
            "change_richtextpage",
            "change_session",
            "change_setting",
            "change_sidebar",
            "change_sidebarbannerwidget",
            "change_sidebarblogcategorywidget",
            "change_sidebartabswidget",
            "change_sidebartwitterwidget",
            "change_site",
            "change_sitepermission",
            "change_socialmediabutton",
            "change_subscriber",
            "change_threadedcomment",
            "change_tweet",
            "change_user",
            "delete_assignedkeyword",
            "delete_blogcategory",
            "delete_blogcategorypage",
            "delete_blogpost",
            "delete_captchastore",
            "delete_columnelement",
            "delete_columnelementwidget",
            "delete_comment",
            "delete_commentflag",
            "delete_contenttype",
            "delete_document",
            "delete_documentlisting",
            "delete_emailsubscriber",
            "delete_emailsubscriberaccesstoken",
            "delete_event",
            "delete_eventcategory",
            "delete_eventcolumnelement",
            "delete_field",
            "delete_fieldentry",
            "delete_form",
            "delete_formentry",
            "delete_gallery",
            "delete_galleryimage",
            "delete_group",
            "delete_homepage",
            "delete_janeusrole",
            "delete_janeussubscriber",
            "delete_janeussubscriberaccesstoken",
            "delete_janeususer",
            "delete_keyword",
            "delete_link",
            "delete_logentry",
            "delete_mailinglist",
            "delete_newsletter",
            "delete_newslettertemplate",
            "delete_newslettertolist",
            "delete_newslettertosubscriber",
            "delete_occurrence",
            "delete_page",
            "delete_pageheaderimagewidget",
            "delete_permission",
            "delete_query",
            "delete_rating",
            "delete_redirect",
            "delete_richtextpage",
            "delete_session",
            "delete_setting",
            "delete_sidebar",
            "delete_sidebarbannerwidget",
            "delete_sidebarblogcategorywidget",
            "delete_sidebartabswidget",
            "delete_sidebartwitterwidget",
            "delete_site",
            "delete_sitepermission",
            "delete_socialmediabutton",
            "delete_subscriber",
            "delete_threadedcomment",
            "delete_tweet",
            "delete_user"
        ])

        save_group_permissions('Master Content Managers', [
#            "add_assignedkeyword",
#            "add_blogcategory",
#            "add_blogcategorypage",
#            "add_blogpost",
#            "add_captchastore",
#            "add_columnelement",
#            "add_columnelementwidget",
#            "add_comment",
#            "add_commentflag",
#            "add_contenttype",
#            "add_document",
#            "add_documentlisting",
            "add_emailsubscriber",
#            "add_emailsubscriberaccesstoken",
#            "add_event",
#            "add_eventcategory",
#            "add_eventcolumnelement",
#            "add_field",
#            "add_fieldentry",
#            "add_form",
#            "add_formentry",
#            "add_gallery",
#            "add_galleryimage",
#            "add_group",
#            "add_homepage",
#            "add_janeusrole",
#            "add_janeussubscriber",
#            "add_janeussubscriberaccesstoken",
#            "add_janeususer",
#            "add_keyword",
#            "add_link",
#            "add_logentry",
#            "add_mailinglist",
#            "add_newsletter",
            "add_newslettertemplate",
            "add_newslettertolist",
            "add_newslettertosubscriber",
#            "add_occurrence",
#            "add_page",
#            "add_pageheaderimagewidget",
#            "add_permission",
#            "add_query",
#            "add_rating",
#            "add_redirect",
#            "add_richtextpage",
#            "add_session",
#            "add_setting",
#            "add_sidebar",
            "add_sidebarbannerwidget",
#            "add_sidebarblogcategorywidget",
#            "add_sidebartabswidget",
#            "add_sidebartwitterwidget",
#            "add_site",
#            "add_sitepermission",
#            "add_socialmediabutton",
#            "add_subscriber",
#            "add_threadedcomment",
#            "add_tweet",
#            "add_user",
#            "can_moderate",
#            "change_assignedkeyword",
#            "change_blogcategory",
#            "change_blogcategorypage",
#            "change_blogpost",
#            "change_captchastore",
#            "change_columnelement",
#            "change_columnelementwidget",
#            "change_comment",
#            "change_commentflag",
#            "change_contenttype",
#            "change_document",
#            "change_documentlisting",
            "change_emailsubscriber",
#            "change_emailsubscriberaccesstoken",
#            "change_event",
#            "change_eventcategory",
#            "change_eventcolumnelement",
#            "change_field",
#            "change_fieldentry",
#            "change_form",
#            "change_formentry",
#            "change_gallery",
#            "change_galleryimage",
#            "change_group",
#            "change_homepage",
#            "change_janeusrole",
            "change_janeussubscriber",
#            "change_janeussubscriberaccesstoken",
#            "change_janeususer",
#            "change_keyword",
#            "change_link",
#            "change_logentry",
#            "change_mailinglist",
#            "change_newsletter",
            "change_newslettertemplate",
            "change_newslettertolist",
            "change_newslettertosubscriber",
#            "change_occurrence",
#            "change_page",
#            "change_pageheaderimagewidget",
#            "change_permission",
#            "change_query",
#            "change_rating",
#            "change_redirect",
#            "change_richtextpage",
#            "change_session",
#            "change_setting",
#            "change_sidebar",
            "change_sidebarbannerwidget",
#            "change_sidebarblogcategorywidget",
#            "change_sidebartabswidget",
#            "change_sidebartwitterwidget",
#            "change_site",
#            "change_sitepermission",
#            "change_socialmediabutton",
#            "change_subscriber",
#            "change_threadedcomment",
#            "change_tweet",
#            "change_user",
#            "delete_assignedkeyword",
#            "delete_blogcategory",
#            "delete_blogcategorypage",
#            "delete_blogpost",
#            "delete_captchastore",
#            "delete_columnelement",
#            "delete_columnelementwidget",
#            "delete_comment",
#            "delete_commentflag",
#            "delete_contenttype",
#            "delete_document",
#            "delete_documentlisting",
            "delete_emailsubscriber",
#            "delete_emailsubscriberaccesstoken",
#            "delete_event",
#            "delete_eventcategory",
#            "delete_eventcolumnelement",
#            "delete_field",
#            "delete_fieldentry",
#            "delete_form",
#            "delete_formentry",
#            "delete_gallery",
#            "delete_galleryimage",
#            "delete_group",
#            "delete_homepage",
#            "delete_janeusrole",
#            "delete_janeussubscriber",
#            "delete_janeussubscriberaccesstoken",
#            "delete_janeususer",
#            "delete_keyword",
#            "delete_link",
#            "delete_logentry",
#            "delete_mailinglist",
#            "delete_newsletter",
            "delete_newslettertemplate",
            "delete_newslettertolist",
            "delete_newslettertosubscriber",
#            "delete_occurrence",
#            "delete_page",
#            "delete_pageheaderimagewidget",
#            "delete_permission",
#            "delete_query",
#            "delete_rating",
#            "delete_redirect",
#            "delete_richtextpage",
#            "delete_session",
#            "delete_setting",
#            "delete_sidebar",
            "delete_sidebarbannerwidget",
#            "delete_sidebarblogcategorywidget",
#            "delete_sidebartabswidget",
#            "delete_sidebartwitterwidget",
#            "delete_site",
#            "delete_sitepermission",
#            "delete_socialmediabutton"
#            "delete_subscriber",
#            "delete_threadedcomment",
#            "delete_tweet",
#            "delete_user"
        ])

        save_group_permissions('Content Managers', [
#            "add_assignedkeyword",
#            "add_blogcategory",
            "add_blogcategorypage",
            "add_blogpost",
#            "add_captchastore",
#            "add_columnelement",
            "add_columnelementwidget",
#            "add_comment",
#            "add_commentflag",
#            "add_contenttype",
            "add_document",
            "add_documentlisting",
#            "add_emailsubscriber",
#            "add_emailsubscriberaccesstoken",
            "add_event",
#            "add_eventcategory",
#            "add_eventcolumnelement",
            "add_field",
            "add_fieldentry",
            "add_form",
            "add_formentry",
#            "add_gallery",
#            "add_galleryimage",
#            "add_group",
#            "add_homepage",
#            "add_janeusrole",
#            "add_janeussubscriber",
#            "add_janeussubscriberaccesstoken",
#            "add_janeususer",
#            "add_keyword",
            "add_link",
#            "add_logentry",
#            "add_mailinglist",
            "add_newsletter",
#            "add_newslettertemplate",
            "add_newslettertolist",
#            "add_newslettertosubscriber",
            "add_occurrence",
            "add_page",
            "add_pageheaderimagewidget",
#            "add_permission",
#            "add_query",
#            "add_rating",
#            "add_redirect",
            "add_richtextpage",
#            "add_session",
#            "add_setting",
#            "add_sidebar",
#            "add_sidebarbannerwidget",
            "add_sidebarblogcategorywidget",
#            "add_sidebartabswidget",
#            "add_sidebartwitterwidget",
#            "add_site",
#            "add_sitepermission",
            "add_socialmediabutton",
#            "add_subscriber",
#            "add_threadedcomment",
#            "add_tweet",
#            "add_user",
#            "can_moderate",
#            "change_assignedkeyword",
#            "change_blogcategory",
            "change_blogcategorypage",
            "change_blogpost",
#            "change_captchastore",
#            "change_columnelement",
            "change_columnelementwidget",
#            "change_comment",
#            "change_commentflag",
#            "change_contenttype",
            "change_document",
            "change_documentlisting",
#            "change_emailsubscriber",
#            "change_emailsubscriberaccesstoken",
            "change_event",
#            "change_eventcategory",
#            "change_eventcolumnelement",
            "change_field",
            "change_fieldentry",
            "change_form",
            "change_formentry",
#            "change_gallery",
#            "change_galleryimage",
#            "change_group",
            "change_homepage",
#            "change_janeusrole",
#            "change_janeussubscriber",
#            "change_janeussubscriberaccesstoken",
#            "change_janeususer",
#            "change_keyword",
            "change_link",
#            "change_logentry",
#            "change_mailinglist",
            "change_newsletter",
#            "change_newslettertemplate",
#            "change_newslettertolist",
#            "change_newslettertosubscriber",
            "change_occurrence",
            "change_page",
            "change_pageheaderimagewidget",
#            "change_permission",
#            "change_query",
#            "change_rating",
#            "change_redirect",
            "change_richtextpage",
#            "change_session",
#            "change_setting",
            "change_sidebar",
#            "change_sidebarbannerwidget",
            "change_sidebarblogcategorywidget",
#            "change_sidebartabswidget",
            "change_sidebartwitterwidget",
#            "change_site",
#            "change_sitepermission",
            "change_socialmediabutton",
#            "change_subscriber",
#            "change_threadedcomment",
#            "change_tweet",
#            "change_user",
#            "delete_assignedkeyword",
#            "delete_blogcategory",
            "delete_blogcategorypage",
            "delete_blogpost",
#            "delete_captchastore",
#            "delete_columnelement",
            "delete_columnelementwidget",
#            "delete_comment",
#            "delete_commentflag",
#            "delete_contenttype",
            "delete_document",
            "delete_documentlisting",
#            "delete_emailsubscriber",
#            "delete_emailsubscriberaccesstoken",
            "delete_event",
#            "delete_eventcategory",
#            "delete_eventcolumnelement",
            "delete_field",
            "delete_fieldentry",
            "delete_form",
            "delete_formentry",
#            "delete_gallery",
#            "delete_galleryimage",
#            "delete_group",
#            "delete_homepage",
#            "delete_janeusrole",
#            "delete_janeussubscriber",
#            "delete_janeussubscriberaccesstoken",
#            "delete_janeususer",
#            "delete_keyword",
            "delete_link",
#            "delete_logentry",
#            "delete_mailinglist",
            "delete_newsletter",
#            "delete_newslettertemplate",
#            "delete_newslettertolist",
#            "delete_newslettertosubscriber",
            "delete_occurrence",
            "delete_page",
            "delete_pageheaderimagewidget",
#            "delete_permission",
#            "delete_query",
#            "delete_rating",
#            "delete_redirect",
            "delete_richtextpage",
#            "delete_session",
#            "delete_setting",
#            "delete_sidebar",
#            "delete_sidebarbannerwidget",
            "delete_sidebarblogcategorywidget",
#            "delete_sidebartabswidget",
#            "delete_sidebartwitterwidget",
#            "delete_site",
#            "delete_sitepermission",
            "delete_socialmediabutton"
#            "delete_subscriber",
#            "delete_threadedcomment",
#            "delete_tweet",
#            "delete_user"
        ])

        save_group_permissions('Publishers', [
#            "add_assignedkeyword",
#            "add_blogcategory",
#            "add_blogcategorypage",
            "add_blogpost",
#            "add_captchastore",
#            "add_columnelement",
#            "add_columnelementwidget",
#            "add_comment",
#            "add_commentflag",
#            "add_contenttype",
#            "add_document",
#            "add_documentlisting",
#            "add_emailsubscriber",
#            "add_emailsubscriberaccesstoken",
            "add_event",
#            "add_eventcategory",
#            "add_eventcolumnelement",
#            "add_field",
#            "add_fieldentry",
#            "add_form",
#            "add_formentry",
#            "add_gallery",
#            "add_galleryimage",
#            "add_group",
#            "add_homepage",
#            "add_janeusrole",
#            "add_janeussubscriber",
#            "add_janeussubscriberaccesstoken",
#            "add_janeususer",
#            "add_keyword",
#            "add_link",
#            "add_logentry",
#            "add_mailinglist",
#            "add_newsletter",
#            "add_newslettertemplate",
#            "add_newslettertolist",
#            "add_newslettertosubscriber",
            "add_occurrence"
#            "add_page",
#            "add_pageheaderimagewidget",
#            "add_permission",
#            "add_query",
#            "add_rating",
#            "add_redirect",
#            "add_richtextpage",
#            "add_session",
#            "add_setting",
#            "add_sidebar",
#            "add_sidebarbannerwidget",
#            "add_sidebarblogcategorywidget",
#            "add_sidebartabswidget",
#            "add_sidebartwitterwidget",
#            "add_site",
#            "add_sitepermission",
#            "add_socialmediabutton",
#            "add_subscriber",
#            "add_threadedcomment",
#            "add_tweet",
#            "add_user",
#            "can_moderate",
#            "change_assignedkeyword",
#            "change_blogcategory",
#            "change_blogcategorypage",
#            "change_blogpost",
#            "change_captchastore",
#            "change_columnelement",
#            "change_columnelementwidget",
#            "change_comment",
#            "change_commentflag",
#            "change_contenttype",
#            "change_document",
#            "change_documentlisting",
#            "change_emailsubscriber",
#            "change_emailsubscriberaccesstoken",
#            "change_event",
#            "change_eventcategory",
#            "change_eventcolumnelement",
#            "change_field",
#            "change_fieldentry",
#            "change_form",
#            "change_formentry",
#            "change_gallery",
#            "change_galleryimage",
#            "change_group",
#            "change_homepage",
#            "change_janeusrole",
#            "change_janeussubscriber",
#            "change_janeussubscriberaccesstoken",
#            "change_janeususer",
#            "change_keyword",
#            "change_link",
#            "change_logentry",
#            "change_mailinglist",
#            "change_newsletter",
#            "change_newslettertemplate",
#            "change_newslettertolist",
#            "change_newslettertosubscriber",
#            "change_occurrence",
#            "change_page",
#            "change_pageheaderimagewidget",
#            "change_permission",
#            "change_query",
#            "change_rating",
#            "change_redirect",
#            "change_richtextpage",
#            "change_session",
#            "change_setting",
#            "change_sidebar",
#            "change_sidebarbannerwidget",
#            "change_sidebarblogcategorywidget",
#            "change_sidebartabswidget",
#            "change_sidebartwitterwidget",
#            "change_site",
#            "change_sitepermission",
#            "change_socialmediabutton",
#            "change_subscriber",
#            "change_threadedcomment",
#            "change_tweet",
#            "change_user",
#            "delete_assignedkeyword",
#            "delete_blogcategory",
#            "delete_blogcategorypage",
#            "delete_blogpost",
#            "delete_captchastore",
#            "delete_columnelement",
#            "delete_columnelementwidget",
#            "delete_comment",
#            "delete_commentflag",
#            "delete_contenttype",
#            "delete_document",
#            "delete_documentlisting",
#            "delete_emailsubscriber",
#            "delete_emailsubscriberaccesstoken",
#            "delete_event",
#            "delete_eventcategory",
#            "delete_eventcolumnelement",
#            "delete_field",
#            "delete_fieldentry",
#            "delete_form",
#            "delete_formentry",
#            "delete_gallery",
#            "delete_galleryimage",
#            "delete_group",
#            "delete_homepage",
#            "delete_janeusrole",
#            "delete_janeussubscriber",
#            "delete_janeussubscriberaccesstoken",
#            "delete_janeususer",
#            "delete_keyword",
#            "delete_link",
#            "delete_logentry",
#            "delete_mailinglist",
#            "delete_newsletter",
#            "delete_newslettertemplate",
#            "delete_newslettertolist",
#            "delete_newslettertosubscriber",
#            "delete_occurrence",
#            "delete_page",
#            "delete_pageheaderimagewidget",
#            "delete_permission",
#            "delete_query",
#            "delete_rating",
#            "delete_redirect",
#            "delete_richtextpage",
#            "delete_session",
#            "delete_setting",
#            "delete_sidebar",
#            "delete_sidebarbannerwidget",
#            "delete_sidebarblogcategorywidget",
#            "delete_sidebartabswidget",
#            "delete_sidebartwitterwidget",
#            "delete_site",
#            "delete_sitepermission",
#            "delete_socialmediabutton",
#            "delete_subscriber",
#            "delete_threadedcomment",
#            "delete_tweet",
#            "delete_user"
        ])

        save_janeus_role('role-team-ict',
            ['Administrators'],
            [] # Empty sites = permissions on all sites
        )

        save_janeus_role('role-as-landelijk',
            ['Content Managers',
             'Master Content Managers'
            ],
            []
        )

        save_janeus_role('role-as-groningen',
            ['Content Managers'],
            ['groningen.jongedemocraten.nl']
        )

        save_janeus_role('role-as-friesland',
            ['Content Managers'],
            ['friesland.jongedemocraten.nl']
        )

        save_janeus_role('role-as-twente',
            ['Content Managers'],
            ['twente.jongedemocraten.nl']
        )

        save_janeus_role('role-as-arnhemnijmegen',
            ['Content Managers'],
            ['arnhemnijmegen.jongedemocraten.nl']
        )

        save_janeus_role('role-as-limburg',
            ['Content Managers'],
            ['limburg.jongedemocraten.nl']
        )

        save_janeus_role('role-as-brabant',
            ['Content Managers'],
            ['brabant.jongedemocraten.nl']
        )

        save_janeus_role('role-as-leidenhaaglanden',
            ['Content Managers'],
            ['leidenhaaglanden.jongedemocraten.nl']
        )

        save_janeus_role('role-as-amsterdam',
            ['Content Managers'],
            ['amsterdam.jongedemocraten.nl']
        )

        save_janeus_role('role-as-rotterdam',
            ['Content Managers'],
            ['rotterdam.jongedemocraten.nl']
        )

        save_janeus_role('role-as-utrecht',
            ['Content Managers'],
            ['utrecht.jongedemocraten.nl']
        )

        save_janeus_role('role-bestuur-landelijk',
            ['Publishers'],
            ['website.jongedemocraten.nl']
        )

        save_janeus_role('role-bestuur-groningen',
            ['Publishers'],
            ['groningen.jongedemocraten.nl']
        )

        save_janeus_role('role-bestuur-friesland',
            ['Publishers'],
            ['friesland.jongedemocraten.nl']
        )

        save_janeus_role('role-bestuur-twente',
            ['Publishers'],
            ['twente.jongedemocraten.nl']
        )

        save_janeus_role('role-bestuur-limburg',
            ['Publishers'],
            ['limburg.jongedemocraten.nl']
        )

        save_janeus_role('role-bestuur-brabant',
            ['Publishers'],
            ['brabant.jongedemocraten.nl']
        )

        save_janeus_role('role-bestuur-rotterdam',
            ['Publishers'],
            ['rotterdam.jongedemocraten.nl']
        )

        save_janeus_role('role-bestuur-leidenhaaglanden',
            ['Publishers'],
            ['leidenhaaglanden.jongedemocraten.nl']
        )

        save_janeus_role('role-bestuur-amsterdam',
            ['Publishers'],
            ['amsterdam.jongedemocraten.nl']
        )

        save_janeus_role('role-bestuur-utrecht',
            ['Publishers'],
            ['utrecht.jongedemocraten.nl']
        )

        save_janeus_role('role-bestuur-arnhemnijmegen',
            ['Publishers'],
            ['arnhemnijmegen.jongedemocraten.nl']
        )



