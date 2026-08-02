package com.kfu.moodledl;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.Intent;
import android.webkit.CookieManager;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.os.Bundle;

public class LoginActivity extends Activity {

    public static final String EXTRA_SERVER = "server";
    public static final String EXTRA_CODE = "code";

    private WebView web;
    private String server;
    private int code;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        server = getIntent().getStringExtra(EXTRA_SERVER);
        code = getIntent().getIntExtra(EXTRA_CODE, 1);

        web = new WebView(this);
        web.setLayoutParams(new android.view.ViewGroup.LayoutParams(
            android.view.ViewGroup.LayoutParams.MATCH_PARENT,
            android.view.ViewGroup.LayoutParams.MATCH_PARENT));

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true);

        web.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageFinished(WebView view, String url) {
                attemptReturnToken();
            }
        });

        setContentView(web);
        web.loadUrl(server + "/login/index.php");
    }

    private void attemptReturnToken() {
        try {
            String cookie = CookieManager.getInstance().getCookie(server);
            if (cookie == null || !cookie.contains("MoodleSession")) {
                return; // not logged in yet; keep showing the login form
            }
            String session = null;
            for (String part : cookie.split(";")) {
                String t = part.trim();
                if (t.startsWith("MoodleSession")) {
                    int idx = t.indexOf('=');
                    if (idx >= 0) {
                        session = t.substring(idx + 1).trim();
                    }
                    break;
                }
            }
            if (session == null || session.isEmpty()) {
                return;
            }
            Intent data = new Intent();
            data.putExtra("token", session);
            data.putExtra("cookie", cookie);
            setResult(RESULT_OK, data);
            finish();
        } catch (Exception ignored) {
            // transient; keep waiting
        }
    }

    @Override
    public void onBackPressed() {
        if (web.canGoBack()) {
            web.goBack();
        } else {
            setResult(RESULT_CANCELED);
            finish();
        }
    }
}