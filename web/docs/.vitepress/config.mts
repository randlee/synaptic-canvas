import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'Synaptic Canvas',
  description: 'Claude Code Plugin Marketplace Documentation',

  head: [
    ['link', { rel: 'icon', href: '/favicon.ico' }]
  ],

  themeConfig: {
    logo: '/logo.svg',

    nav: [
      { text: 'Home', link: '/' },
      { text: 'Plugins', link: '/plugins/' },
      { text: 'Getting Started', link: '/guide/' }
    ],

    sidebar: {
      '/plugins/': [
        {
          text: 'Plugins',
          items: [
            { text: 'Overview', link: '/plugins/' },
            { text: 'sc-github-issue', link: '/plugins/sc-github-issue' },
            { text: 'sc-git-worktree', link: '/plugins/sc-git-worktree' },
            { text: 'sc-ci-automation', link: '/plugins/sc-ci-automation' },
            { text: 'sc-delay-tasks', link: '/plugins/sc-delay-tasks' },
            { text: 'sc-manage', link: '/plugins/sc-manage' },
            { text: 'sc-repomix-nuget', link: '/plugins/sc-repomix-nuget' }
          ]
        }
      ]
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/randlee/synaptic-canvas' }
    ],

    footer: {
      message: 'Claude Code Plugin Marketplace',
      copyright: 'Copyright 2025'
    },

    search: {
      provider: 'local'
    }
  },

  // Enable Vue components in Markdown
  vue: {
    template: {
      compilerOptions: {
        isCustomElement: (tag) => tag.startsWith('d3-')
      }
    }
  }
})
