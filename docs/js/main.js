/**
 * WhyValue Documentation — Interactivity (Vanilla JS)
 */

document.addEventListener('DOMContentLoaded', () => {
  initThemeToggle();
  initMobileNav();
  initCopyButtons();
});

/**
 * Theme Toggle & Persistence
 */
function initThemeToggle() {
  const themeToggle = document.getElementById('theme-toggle');
  if (!themeToggle) return;

  function updateToggleState(theme) {
    if (theme === 'light') {
      themeToggle.setAttribute('aria-label', 'Switch to dark mode');
      themeToggle.setAttribute('title', 'Switch to dark mode');
    } else {
      themeToggle.setAttribute('aria-label', 'Switch to light mode');
      themeToggle.setAttribute('title', 'Switch to light mode');
    }
  }

  // Get current initial theme from <html> attribute set by inline head script
  const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
  updateToggleState(currentTheme);

  themeToggle.addEventListener('click', () => {
    const activeTheme = document.documentElement.getAttribute('data-theme');
    const nextTheme = activeTheme === 'light' ? 'dark' : 'light';
    
    document.documentElement.setAttribute('data-theme', nextTheme);
    localStorage.setItem('whyvalue_theme', nextTheme);
    updateToggleState(nextTheme);
  });
}

/**
 * Initialize Mobile Sidebar Navigation
 */
function initMobileNav() {
  const menuToggle = document.getElementById('menu-toggle');
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');

  if (!menuToggle || !sidebar || !overlay) return;

  function openSidebar() {
    sidebar.classList.add('open');
    overlay.classList.add('active');
    menuToggle.setAttribute('aria-expanded', 'true');
  }

  function closeSidebar() {
    sidebar.classList.remove('open');
    overlay.classList.remove('active');
    menuToggle.setAttribute('aria-expanded', 'false');
  }

  menuToggle.addEventListener('click', () => {
    const isOpen = sidebar.classList.contains('open');
    if (isOpen) {
      closeSidebar();
    } else {
      openSidebar();
    }
  });

  overlay.addEventListener('click', closeSidebar);

  // Close sidebar when clicking links inside sidebar on mobile
  const sidebarLinks = sidebar.querySelectorAll('a:not(.disabled)');
  sidebarLinks.forEach(link => {
    link.addEventListener('click', () => {
      if (window.innerWidth <= 1024) {
        closeSidebar();
      }
    });
  });

  // Keyboard navigation (Escape closes sidebar)
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && sidebar.classList.contains('open')) {
      closeSidebar();
      menuToggle.focus();
    }
  });
}

/**
 * Initialize Reusable Copy Code Buttons
 */
function initCopyButtons() {
  const copyButtons = document.querySelectorAll('.copy-btn');

  copyButtons.forEach(btn => {
    btn.addEventListener('click', async () => {
      const targetId = btn.getAttribute('data-target');
      let textToCopy = '';

      if (targetId) {
        const targetEl = document.getElementById(targetId);
        if (targetEl) {
          textToCopy = targetEl.innerText || targetEl.textContent;
        }
      } else {
        const codeEl = btn.closest('.code-block-wrapper, .install-box')?.querySelector('code, pre');
        if (codeEl) {
          textToCopy = codeEl.innerText || codeEl.textContent;
        }
      }

      if (!textToCopy) return;

      // Clean prompt symbol if present
      textToCopy = textToCopy.replace(/^\$\s*/, '').trim();

      try {
        await navigator.clipboard.writeText(textToCopy);
        showCopyFeedback(btn);
      } catch (err) {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = textToCopy;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        try {
          document.execCommand('copy');
          showCopyFeedback(btn);
        } catch (fallbackErr) {
          console.error('Failed to copy code', fallbackErr);
        }
        document.body.removeChild(textarea);
      }
    });
  });
}

function showCopyFeedback(btn) {
  const originalText = btn.getAttribute('data-original-text') || btn.innerHTML;
  if (!btn.getAttribute('data-original-text')) {
    btn.setAttribute('data-original-text', originalText);
  }

  btn.classList.add('copied');
  btn.innerHTML = `
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
      <polyline points="20 6 9 17 4 12"></polyline>
    </svg>
    Copied
  `;

  setTimeout(() => {
    btn.classList.remove('copied');
    btn.innerHTML = originalText;
  }, 2000);
}
