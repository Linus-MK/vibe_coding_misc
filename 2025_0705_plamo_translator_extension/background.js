// 拡張機能のアイコンがクリックされたとき、またはコマンドが実行されたときに起動する
chrome.action.onClicked.addListener(handleAction);
chrome.commands.onCommand.addListener(handleAction);

/**
 * 拡張機能のメイン処理
 * @param {chrome.tabs.Tab} tab - アクションが実行されたときのタブ情報
 */
function handleAction(tab) {
  // 選択されたテキストを取得する関数を注入して実行
  chrome.scripting.executeScript(
    {
      target: { tabId: tab.id },
      function: getSelectedText,
    },
    (injectionResults) => {
      // エラーハンドリング
      if (chrome.runtime.lastError || !injectionResults || !injectionResults[0]) {
        console.error("Script injection failed: " + (chrome.runtime.lastError ? chrome.runtime.lastError.message : "No results returned"));
        return;
      }

      const selectedText = injectionResults[0].result;
      if (selectedText) {
        // 翻訳サイトを新しいタブで開く
        const url = "https://translate-demo.plamo.preferredai.jp/";
        chrome.tabs.create({ url: url }, (newTab) => {
          // タブの読み込み完了を監視するリスナーを設定
          const listener = (tabId, changeInfo) => {
            // 作成したタブが完全に読み込まれたら、メッセージを送信
            if (tabId === newTab.id && changeInfo.status === 'complete') {
              chrome.tabs.sendMessage(tabId, { text: selectedText });
              // 一度メッセージを送ったらリスナーは不要なので削除
              chrome.tabs.onUpdated.removeListener(listener);
            }
          };
          chrome.tabs.onUpdated.addListener(listener);
        });
      }
    }
  );
}

/**
 * 現在のページで選択されているテキストを取得する
 * @returns {string} 選択されているテキスト
 */
function getSelectedText() {
  return window.getSelection().toString();
}
