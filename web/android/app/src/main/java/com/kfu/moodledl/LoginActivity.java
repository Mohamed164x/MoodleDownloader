package com.kfu.moodledl;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.webkit.CookieManager;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

public class LoginActivity extends Activity {

    public static final String EXTRA_SERVER = "server";
    private String server;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        server = getIntent().getStringExtra(EXTRA_SERVER);
        if (server == null || server.isEmpty()) {
            server = "https://elearning.kfu.edu.eg";
        }

        CookieManager.getInstance().setAcceptCookie(true);

        WebView web = new WebView(this);
        web.setLayoutParams(new android.view.ViewGroup.LayoutParams(
            android.view.ViewGroup.LayoutParams.MATCH_PARENT,
            android.view.ViewGroup.LayoutParams.MATCH_PARENT));

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);
        s.setAllowFileAccess(true);
        s.setSupportZoom(true);
        s.setBuiltInZoomControls(true);
        s.setDisplayZoomControls(false);

        web.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageFinished(WebView view, String url) {
                // After finishing a page, attempt to capture the session cookie.
                if (tryCaptureToken()) {
                    // captured; onBackPressed will call finish via result already set
                }
            }
        });

        setContentView(web);
        web.loadUrl(server + "/login/index.php");
    }

    private boolean tryCaptureToken() {
        try {
            String cookie = CookieManager.getInstance().getCookie(server);
            if (cookie == null || !cookie.contains("MoodleSession")) {
                return false;
            }
            String session = null;
            String full = "";
            for (String part : cookie.split(";")) {
                String t = part.trim();
                if (!full.isEmpty()) full += "; ";
                full += t;
                if (t.startsWith("MoodleSession")) {
                    int idx = t.indexOf('=');
                    if (idx >= 0) session = t.substring(idx + 1).trim();
                }
            }
            if (session == null || session.isEmpty()) {
                return false;
            }
            Intent data = new Intent();
            data.putExtra("token", session);
            data.putExtra("cookie", full);
            setResult(RESULT_OK, data);
            finish();
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    @Override
    public void onBackPressed() {
        setResult(RESULT_CANCELED);
        finish();
    }
}