package com.kfu.moodledl;

import android.content.Intent;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.ActivityCallback;
import com.getcapacitor.annotation.CapacitorPlugin;

@CapacitorPlugin(name = "MoodleLogin")
public class MoodleLoginPlugin extends Plugin {

    @PluginMethod
    public void login(PluginCall call) {
        String server = call.getString("server", "https://elearning.kfu.edu.eg");
        Intent intent = new Intent(getActivity(), LoginActivity.class);
        intent.putExtra(LoginActivity.EXTRA_SERVER, server);
        intent.putExtra(LoginActivity.EXTRA_CODE, 1);
        startActivityForResult(call, intent, "loginResult");
    }

    @ActivityCallback
    private void loginResult(PluginCall call, Intent data) {
        if (data == null) {
            call.reject("Login cancelled");
            return;
        }
        String token = data.getStringExtra("token");
        String cookie = data.getStringExtra("cookie");
        if (token == null || token.isEmpty()) {
            call.reject("Login failed: no session token captured");
            return;
        }
        com.getcapacitor.JSObject ret = new com.getcapacitor.JSObject();
        ret.put("token", token);
        ret.put("cookie", cookie);
        call.resolve(ret);
    }
}