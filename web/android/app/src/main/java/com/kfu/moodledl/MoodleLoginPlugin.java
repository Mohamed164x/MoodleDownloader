package com.kfu.moodledl;

import android.content.Intent;
import android.net.Uri;
import androidx.activity.result.ActivityResult;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.ActivityCallback;
import com.getcapacitor.annotation.CapacitorPlugin;

@CapacitorPlugin(name = "MoodleLogin")
public class MoodleLoginPlugin extends Plugin {

    @PluginMethod
    public void login(PluginCall call) {
        try {
            String server = call.getString("server", "https://elearning.kfu.edu.eg");
            Intent intent = new Intent(getActivity(), LoginActivity.class);
            intent.putExtra(LoginActivity.EXTRA_SERVER, server);
            startActivityForResult(call, intent, "loginResult");
        } catch (Throwable t) {
            call.reject("Login failed: " + t.getMessage());
        }
    }

    @PluginMethod
    public void openBrowser(PluginCall call) {
        try {
            String url = call.getString("url");
            Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            getContext().startActivity(intent);
            call.resolve();
        } catch (Throwable t) {
            call.reject("Could not open browser: " + t.getMessage());
        }
    }

    @ActivityCallback
    private void loginResult(PluginCall call, ActivityResult result) {
        try {
            if (call == null) return;
            if (result == null || result.getData() == null) {
                call.reject("Login cancelled");
                return;
            }
            Intent data = result.getData();
            String token = data.getStringExtra("token");
            String cookie = data.getStringExtra("cookie");
            if (token == null || token.isEmpty()) {
                call.reject("Login failed: no session token captured");
                return;
            }
            JSObject ret = new JSObject();
            ret.put("token", token);
            ret.put("cookie", cookie);
            call.resolve(ret);
        } catch (Throwable t) {
            if (call != null) call.reject("Login result error: " + t.getMessage());
        }
    }
}