// IPTV 應用主程序
(function() {
    'use strict';

    // 全局狀態
    const state = {
        currentPage: 'home',
        currentCategory: null,
        currentChannel: null
    };

    // DOM 元素緩存
    const elements = {
        pages: {
            home: document.getElementById('page-home'),
            category: document.getElementById('page-category')
        },
        categoryTitle: document.getElementById('category-title'),
        channelList: document.getElementById('channel-list'),
        searchInput: document.getElementById('search-input'),
        btnBackCategory: document.getElementById('btn-back-category')
    };

    // 初始化
    function init() {
        bindEvents();
        handleHashChange();
        window.addEventListener('hashchange', handleHashChange);
    }

    // 綁定事件
    function bindEvents() {
        // 返回按鈕
        elements.btnBackCategory.addEventListener('click', function(e) {
            e.preventDefault();
            navigateTo('home');
        });

        // 搜索功能
        elements.searchInput.addEventListener('input', function() {
            filterChannels(this.value);
        });
    }

    // 路由處理
    function handleHashChange() {
        const hash = window.location.hash.slice(1) || 'home';
        const parts = hash.split('/');
        const action = parts[0];
        const param = parts[1];

        switch(action) {
            case 'home':
                navigateTo('home');
                break;
            case 'category':
                navigateTo('category', param);
                break;
            default:
                navigateTo('home');
        }
    }

    // 頁面導航
    function navigateTo(page, param) {
        // 隱藏所有頁面
        Object.values(elements.pages).forEach(function(p) {
            p.classList.remove('active');
        });

        state.currentPage = page;

        switch(page) {
            case 'home':
                elements.pages.home.classList.add('active');
                window.location.hash = 'home';
                break;

            case 'category':
                state.currentCategory = param;
                showCategory(param);
                elements.pages.category.classList.add('active');
                window.location.hash = 'category/' + param;
                break;
        }

        // 滾動到頂部
        window.scrollTo(0, 0);
    }

    // 顯示分類頁面
    function showCategory(categoryId) {
        const category = CHANNELS_DATA[categoryId];
        if (!category) {
            elements.categoryTitle.textContent = '未知分類';
            elements.channelList.innerHTML = '<li class="loading">暫無頻道數據</li>';
            return;
        }

        elements.categoryTitle.textContent = category.name;
        elements.searchInput.value = '';
        renderChannelList(category.channels);
    }

    // 渲染頻道列表
    function renderChannelList(channels) {
        if (!channels || channels.length === 0) {
            elements.channelList.innerHTML = '<li class="loading">暫無頻道數據</li>';
            return;
        }

        let html = '';
        channels.forEach(function(channel) {
            var url = 'player/' + state.currentCategory + '/' + channel.id;
            html += '<li>' +
                '<a href="' + url + '" data-channel-id="' + channel.id + '" target="_blank" rel="noopener">' +
                channel.name +
                '</a></li>';
        });

        elements.channelList.innerHTML = html;
    }

    // 過濾頻道
    function filterChannels(keyword) {
        if (!state.currentCategory) return;

        const category = CHANNELS_DATA[state.currentCategory];
        if (!category) return;

        if (!keyword.trim()) {
            renderChannelList(category.channels);
            return;
        }

        const filtered = category.channels.filter(function(channel) {
            return channel.name.toLowerCase().includes(keyword.toLowerCase());
        });

        renderChannelList(filtered);
    }

    // 啟動應用
    document.addEventListener('DOMContentLoaded', init);

})();
