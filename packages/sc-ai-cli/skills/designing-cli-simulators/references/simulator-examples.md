# Simulator Examples

Use these examples when you need a concrete starting pattern for a simple but stateful simulator.

These are genericized patterns adapted from real simulator code, with renamed types and namespaces. They are starting points, not drop-in production code.

## Map-Backed Request Handler Pattern

For small text or binary protocols, a good baseline is:
- one request-handler interface
- one transport loop
- one state object
- one map-backed dispatch table

The handler owns command dispatch. State lives in a separate object or in captured delegates. The simulator loop only moves messages in and out.

## Example Interface

```csharp
public interface IRequestHandler<TMessage>
{
    TMessage? Handle(TMessage request);
}
```

This shape is useful when:
- some requests return immediate replies
- some commands mutate state and return no reply
- the transport layer should stay dumb

## Example Map-Backed Handler

```csharp
using System;
using System.Collections.Generic;

namespace Example.DeviceSimulation;

public sealed class DeviceState
{
    public string Mode { get; set; } = "idle";
    public bool Online { get; set; } = true;
}

public sealed class MapBackedRequestHandler : IRequestHandler<string>
{
    private readonly DeviceState _state;
    private readonly IDictionary<string, Func<string?, string?>> _handlers;

    public MapBackedRequestHandler(DeviceState state)
    {
        _state = state;
        _handlers = new Dictionary<string, Func<string?, string?>>(StringComparer.OrdinalIgnoreCase)
        {
            ["PING"] = _ => "PONG",
            ["GET:MODE"] = _ => _state.Mode,
            ["SET:MODE"] = arg =>
            {
                if (string.IsNullOrWhiteSpace(arg))
                {
                    return "ERR missing mode";
                }

                _state.Mode = arg.Trim();
                return "OK";
            },
            ["GET:ONLINE"] = _ => _state.Online ? "true" : "false",
            ["SET:OFFLINE"] = _ =>
            {
                _state.Online = false;
                return null;
            }
        };
    }

    public string? Handle(string request)
    {
        var normalized = request.Trim();
        var separator = normalized.IndexOf(' ');
        var key = separator >= 0 ? normalized[..separator] : normalized;
        var arg = separator >= 0 ? normalized[(separator + 1)..] : null;

        if (!_handlers.TryGetValue(key, out var handler))
        {
            return $"ERR unknown command: {key}";
        }

        return handler(arg);
    }
}
```

Important details:
- normalize before lookup
- keep state outside the dispatch map itself
- let queries read current state
- let commands mutate state and optionally return no reply

## Example Transport Loop

```csharp
public sealed class TextProtocolSimulator
{
    private readonly IRequestHandler<string> _handler;

    public TextProtocolSimulator(IRequestHandler<string> handler)
    {
        _handler = handler;
    }

    public string? Accept(string request)
    {
        return _handler.Handle(request);
    }
}
```

In a real implementation, `Accept` may read from serial, TCP, USB, or a higher-level transport abstraction. The key design point is the same: transport forwards requests, handler owns behavior.

## Why This Pattern Works

This is a good baseline when:
- the protocol is command/response oriented
- the state model is small enough to keep explicit
- you need deterministic tests
- you want to inject alternate behaviors by swapping handlers or state

It is also easy to extend with:
- latency injection
- temporary disconnects
- command-specific failures
- invalid-state transitions

## Translation Notes

Equivalent shapes in other languages:
- Rust: `trait RequestHandler<TMessage> { fn handle(&mut self, request: TMessage) -> Option<TMessage>; }`
- Go: `type RequestHandler interface { Handle(request string) *string }`

The invariant matters more than the exact syntax:
- normalized request in
- typed or well-defined reply out
- persistent state between calls
- no separate business logic path for simulation
