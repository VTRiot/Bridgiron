/**
 * Bridgiron - ChatGPT応答プロンプト抽出用ブックマークレット
 *
 * 機能: ChatGPTの最後の応答からプロンプト部分を抽出してクリップボードにコピー
 * 対象: https://chat.openai.com/ または https://chatgpt.com/
 * 処理: HTML取得 → Markdown変換 → SOP/EOPマーカー検出 → 抽出 → コピー
 */
(function() {
    // ========================================
    // パターン定義（GUIで生成時に差し替え可能）
    // ========================================
    var PATTERNS = {
        // 新方式（最優先）
        startMarker: "---SOP---",
        endMarker: "---EOP---",

        // フォールバック用（従来方式）
        phrases: [
            "ClaudeCodeに投げるプロンプト",
            "プロンプト（完成形）",
            "以下を実行して",
            "以下のプロンプト",
            "以下の指示"
        ],
        delimiters: [
            "---"
        ],
        keywords: [
            "目的：",
            "前提：",
            "完了条件：",
            "対象：",
            "要件：",
            "作業範囲：",
            "受入条件：",
            "方針：",
            "実装仕様："
        ]
    };

    // ========================================
    // 通知表示関数（3色対応：緑、黄、赤）
    // ========================================
    function showNotification(message, type) {
        var notification = document.createElement('div');
        notification.textContent = message;

        var bgColor;
        if (type === 'success') {
            bgColor = '#10a37f'; // 緑
        } else if (type === 'fallback') {
            bgColor = '#f59e0b'; // 黄色
        } else {
            bgColor = '#ef4444'; // 赤
        }

        notification.style.cssText =
            'position:fixed;' +
            'top:16px;' +
            'right:16px;' +
            'padding:12px 20px;' +
            'border-radius:8px;' +
            'font-size:14px;' +
            'font-weight:500;' +
            'z-index:999999;' +
            'transition:opacity 0.3s;' +
            'box-shadow:0 4px 12px rgba(0,0,0,0.15);' +
            'background:' + bgColor + ';color:#fff;';

        document.body.appendChild(notification);

        setTimeout(function() {
            notification.style.opacity = '0';
            setTimeout(function() {
                notification.remove();
            }, 300);
        }, 2000);
    }

    // ========================================
    // HTML→Markdown変換関数
    // ========================================
    function htmlToMarkdown(html) {
        // 一時的なDOM要素を作成
        var temp = document.createElement('div');
        temp.innerHTML = html;

        // コードブロック（pre > code）を先に処理
        var preBlocks = temp.querySelectorAll('pre');
        preBlocks.forEach(function(pre) {
            var code = pre.querySelector('code');
            var codeText = code ? code.textContent : pre.textContent;
            // 言語クラスを取得（あれば）
            var langClass = code ? code.className.match(/language-(\w+)/) : null;
            var lang = langClass ? langClass[1] : '';
            pre.outerHTML = '\n```' + lang + '\n' + codeText + '\n```\n';
        });

        // 見出しタグを変換
        for (var i = 1; i <= 6; i++) {
            var headers = temp.querySelectorAll('h' + i);
            headers.forEach(function(h) {
                var hashes = '#'.repeat(i);
                h.outerHTML = '\n' + hashes + ' ' + h.textContent + '\n';
            });
        }

        // 強調タグを変換
        temp.querySelectorAll('strong, b').forEach(function(el) {
            el.outerHTML = '**' + el.textContent + '**';
        });

        // 斜体タグを変換
        temp.querySelectorAll('em, i').forEach(function(el) {
            el.outerHTML = '*' + el.textContent + '*';
        });

        // インラインコードを変換
        temp.querySelectorAll('code').forEach(function(el) {
            el.outerHTML = '`' + el.textContent + '`';
        });

        // リンクを変換
        temp.querySelectorAll('a').forEach(function(el) {
            var href = el.getAttribute('href') || '';
            var text = el.textContent;
            el.outerHTML = '[' + text + '](' + href + ')';
        });

        // リスト処理（再帰的にネスト対応）
        function processList(list, indent) {
            indent = indent || 0;
            var result = '';
            var items = list.children;
            var isOrdered = list.tagName.toLowerCase() === 'ol';
            var counter = 1;

            for (var j = 0; j < items.length; j++) {
                var item = items[j];
                if (item.tagName.toLowerCase() === 'li') {
                    var prefix = '  '.repeat(indent) + (isOrdered ? (counter++) + '. ' : '- ');
                    // ネストされたリストを探す
                    var nestedList = item.querySelector('ul, ol');
                    var itemText = '';

                    // テキストノードを取得
                    for (var k = 0; k < item.childNodes.length; k++) {
                        var child = item.childNodes[k];
                        if (child.nodeType === 3) { // テキストノード
                            itemText += child.textContent.trim();
                        } else if (child.tagName && !['UL', 'OL'].includes(child.tagName.toUpperCase())) {
                            itemText += child.textContent.trim();
                        }
                    }

                    result += prefix + itemText + '\n';

                    // ネストされたリストを処理
                    if (nestedList) {
                        result += processList(nestedList, indent + 1);
                    }
                }
            }
            return result;
        }

        // トップレベルのリストを処理
        temp.querySelectorAll('body > ul, body > ol, div > ul, div > ol').forEach(function(list) {
            if (!list.parentElement || !['LI'].includes(list.parentElement.tagName)) {
                list.outerHTML = '\n' + processList(list, 0);
            }
        });

        // 残りのul/olを処理（ネストされていないもの）
        temp.querySelectorAll('ul, ol').forEach(function(list) {
            list.outerHTML = '\n' + processList(list, 0);
        });

        // 段落と改行を処理
        temp.querySelectorAll('p').forEach(function(el) {
            el.outerHTML = el.textContent + '\n\n';
        });

        temp.querySelectorAll('br').forEach(function(el) {
            el.outerHTML = '\n';
        });

        // divを改行に変換
        temp.querySelectorAll('div').forEach(function(el) {
            el.outerHTML = el.innerHTML + '\n';
        });

        // 残りのタグを除去してテキストを取得
        var result = temp.textContent || temp.innerText || '';

        // 連続する改行を整理（3つ以上を2つに）
        result = result.replace(/\n{3,}/g, '\n\n');

        // 先頭・末尾の空白を除去
        result = result.trim();

        return result;
    }

    // ========================================
    // プロンプト抽出関数（SOP/EOP方式 + フォールバック）
    // ========================================
    function extractPrompt(markdown) {
        var lines = markdown.split('\n');
        var sopIndex = -1;
        var eopIndex = -1;

        // 1. SOP/EOPマーカーを検索
        for (var i = 0; i < lines.length; i++) {
            var trimmedLine = lines[i].trim();
            if (trimmedLine === PATTERNS.startMarker) {
                sopIndex = i;
            }
            if (trimmedLine === PATTERNS.endMarker) {
                eopIndex = i;
            }
        }

        // 2. SOP/EOP両方が見つかった場合（新方式）
        if (sopIndex !== -1 && eopIndex !== -1 && sopIndex < eopIndex) {
            var extracted = lines.slice(sopIndex + 1, eopIndex).join('\n').trim();
            if (extracted) {
                return { text: extracted, method: 'marker' };
            }
        }

        // 3. SOPのみ見つかった場合（EOPがない）→ SOPから末尾まで
        if (sopIndex !== -1) {
            var extracted = lines.slice(sopIndex + 1).join('\n').trim();
            if (extracted) {
                return { text: extracted, method: 'marker' };
            }
        }

        // 4. フォールバック：フレーズによる識別
        for (var p = 0; p < PATTERNS.phrases.length; p++) {
            var phrase = PATTERNS.phrases[p];
            for (var i = 0; i < lines.length; i++) {
                if (lines[i].indexOf(phrase) !== -1) {
                    var extracted = lines.slice(i + 1).join('\n').trim();
                    if (extracted) {
                        return { text: extracted, method: 'fallback' };
                    }
                }
            }
        }

        // 5. フォールバック：区切り文字による識別（最後の区切り文字を使用）
        for (var d = 0; d < PATTERNS.delimiters.length; d++) {
            var delimiter = PATTERNS.delimiters[d];
            var lastDelimiterIndex = -1;
            for (var i = 0; i < lines.length; i++) {
                if (lines[i].trim() === delimiter) {
                    lastDelimiterIndex = i;
                }
            }
            if (lastDelimiterIndex !== -1) {
                var extracted = lines.slice(lastDelimiterIndex + 1).join('\n').trim();
                if (extracted) {
                    return { text: extracted, method: 'fallback' };
                }
            }
        }

        // 6. フォールバック：キーワードによる識別（最初に見つかったキーワードを使用）
        for (var k = 0; k < PATTERNS.keywords.length; k++) {
            var keyword = PATTERNS.keywords[k];
            for (var i = 0; i < lines.length; i++) {
                if (lines[i].indexOf(keyword) !== -1) {
                    var extracted = lines.slice(i).join('\n').trim();
                    if (extracted) {
                        return { text: extracted, method: 'fallback' };
                    }
                }
            }
        }

        // 7. 識別失敗
        return null;
    }

    // ========================================
    // メイン処理
    // ========================================
    try {
        // ChatGPTの応答要素を取得
        var responses = document.querySelectorAll('[data-message-author-role="assistant"]');

        if (!responses || responses.length === 0) {
            showNotification('コピーに失敗しました（応答が見つかりません）', 'error');
            return;
        }

        // 最後の応答を取得（HTML形式）
        var lastResponse = responses[responses.length - 1];
        var html = lastResponse.innerHTML;

        if (!html || html.trim() === '') {
            showNotification('コピーに失敗しました（空の応答）', 'error');
            return;
        }

        // HTML→Markdown変換
        var markdown = htmlToMarkdown(html);

        // プロンプト抽出
        var result = extractPrompt(markdown);

        if (!result) {
            showNotification('プロンプトが見つかりませんでした', 'error');
            return;
        }

        // クリップボードにコピー（識別子付きでBridgironが検知可能に）
        navigator.clipboard.writeText('[BRIDGIRON_GPT2CC]\n' + result.text).then(function() {
            if (result.method === 'marker') {
                showNotification('プロンプトを抽出しました', 'success');
            } else {
                showNotification('プロンプトを抽出しました（従来方式）', 'fallback');
            }
        }).catch(function(err) {
            showNotification('コピーに失敗しました', 'error');
            console.error('Bridgiron extract error:', err);
        });

    } catch (e) {
        showNotification('コピーに失敗しました', 'error');
        console.error('Bridgiron error:', e);
    }
})();
